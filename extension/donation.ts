/**
 * Donation system for Enhanced Shinigami Eyes
 * 
 * This module handles the donation prompts and Stripe integration
 * while maintaining complete user privacy.
 * 
 * No user data is collected or stored on servers.
 */

// Donation prompt state stored in local storage
interface DonationState {
  lastPromptDate: number;         // Timestamp of last prompt
  donationCount: number;          // Number of completed donations
  recurringActive: boolean;       // Whether a recurring donation is active
  recurringToken?: string;        // Anonymous Stripe token for verification
  promptDisabled: boolean;        // Whether prompts are permanently disabled
}

// Default donation state
const DEFAULT_DONATION_STATE: DonationState = {
  lastPromptDate: 0,
  donationCount: 0,
  recurringActive: false,
  promptDisabled: false
};

// Donation service URLs
const DONATION_API_URL = 'https://api.shini-eyes-enhanced.org/donation';
const STRIPE_PUBLIC_KEY = 'pk_live_REPLACE_WITH_REAL_KEY';

/**
 * Donation Manager
 * Handles all donation-related functionality
 */
export class DonationManager {
  private state: DonationState;
  
  constructor() {
    this.state = this.loadState();
  }
  
  /**
   * Load donation state from storage
   */
  private loadState(): DonationState {
    try {
      const storedState = localStorage.getItem('shini_donation_state');
      if (storedState) {
        return JSON.parse(storedState);
      }
    } catch (e) {
      console.error('Failed to load donation state', e);
    }
    
    return { ...DEFAULT_DONATION_STATE };
  }
  
  /**
   * Save donation state to storage
   */
  private saveState(): void {
    try {
      localStorage.setItem('shini_donation_state', JSON.stringify(this.state));
    } catch (e) {
      console.error('Failed to save donation state', e);
    }
  }
  
  /**
   * Check if we should show the donation prompt
   */
  shouldShowPrompt(): boolean {
    // Never show if permanently disabled
    if (this.state.promptDisabled) {
      return false;
    }
    
    // Never show if recurring donation is active
    if (this.state.recurringActive && this.state.recurringToken) {
      this.verifyRecurringToken(); // Verify in background
      return false;
    }
    
    // Check if 30 days have passed since last prompt
    const now = Date.now();
    const daysSinceLastPrompt = (now - this.state.lastPromptDate) / (1000 * 60 * 60 * 24);
    
    return daysSinceLastPrompt >= 30;
  }
  
  /**
   * Show the donation prompt
   */
  async showDonationPrompt(): Promise<void> {
    // Mark as prompted
    this.state.lastPromptDate = Date.now();
    this.saveState();
    
    // Create and display the donation modal
    const modal = document.createElement('div');
    modal.className = 'shini-donation-modal';
    modal.innerHTML = `
      <div class="shini-donation-content">
        <h2>Support Enhanced Shinigami Eyes</h2>
        <p>You've been using the enhanced features of Shinigami Eyes for 30 days. 
           These features require server resources to provide ML-powered analysis.</p>
        <p>Would you consider supporting this project with a donation to help cover costs?</p>
        <p>This project will always remain free and open source, but your support helps keep it running!</p>
        <div class="shini-donation-buttons">
          <button id="shini-donate-one-time">One-time Donation</button>
          <button id="shini-donate-recurring">Monthly Support</button>
          <button id="shini-donate-later">Remind me later</button>
          <button id="shini-donate-never">Don't show again</button>
        </div>
        <p class="shini-privacy-notice">Note: We don't collect any personal data. All donation processing is handled securely by Stripe.</p>
      </div>
    `;
    
    document.body.appendChild(modal);
    
    // Add event listeners
    document.getElementById('shini-donate-one-time')?.addEventListener('click', () => {
      this.handleOneTimeDonation();
      document.body.removeChild(modal);
    });
    
    document.getElementById('shini-donate-recurring')?.addEventListener('click', () => {
      this.handleRecurringDonation();
      document.body.removeChild(modal);
    });
    
    document.getElementById('shini-donate-later')?.addEventListener('click', () => {
      document.body.removeChild(modal);
    });
    
    document.getElementById('shini-donate-never')?.addEventListener('click', () => {
      this.disablePrompts();
      document.body.removeChild(modal);
    });
  }
  
  /**
   * Handle one-time donation
   */
  private async handleOneTimeDonation(): Promise<void> {
    const success = await this.openStripeDonationPage(false);
    
    if (success) {
      this.state.donationCount++;
      
      // Check if we've reached 5 donations
      if (this.state.donationCount >= 5) {
        this.disablePrompts();
      }
      
      this.saveState();
    }
  }
  
  /**
   * Handle recurring donation
   */
  private async handleRecurringDonation(): Promise<void> {
    const success = await this.openStripeDonationPage(true);
    
    if (success) {
      // We'll get the recurring token from the success callback URL
      this.state.donationCount++;
      this.state.recurringActive = true;
      
      // Check if we've reached 5 donations
      if (this.state.donationCount >= 5) {
        this.disablePrompts();
      }
      
      this.saveState();
    }
  }
  
  /**
   * Open Stripe donation page
   */
  private async openStripeDonationPage(recurring: boolean): Promise<boolean> {
    return new Promise((resolve) => {
      // Generate a random session ID for this donation attempt
      // This doesn't identify the user, just the browser session
      const sessionId = Math.random().toString(36).substring(2, 15);
      
      // Open Stripe checkout in a popup
      const donationType = recurring ? 'recurring' : 'one-time';
      const stripeUrl = `https://checkout.stripe.com/pay/${STRIPE_PUBLIC_KEY}?client_reference_id=${sessionId}&donation_type=${donationType}`;
      
      const popup = window.open(stripeUrl, 'shini_donation', 'width=600,height=600');
      
      // Handle donation completion via message passing
      window.addEventListener('message', (event) => {
        // Only accept messages from our expected origins
        if (event.origin !== 'https://checkout.stripe.com' && 
            event.origin !== 'https://api.shini-eyes-enhanced.org') {
          return;
        }
        
        if (event.data.type === 'donation_complete') {
          if (recurring && event.data.recurringToken) {
            this.state.recurringToken = event.data.recurringToken;
          }
          
          if (popup) {
            popup.close();
          }
          
          resolve(true);
        }
      }, { once: true });
      
      // Handle popup being closed without completion
      const checkClosed = setInterval(() => {
        if (popup && popup.closed) {
          clearInterval(checkClosed);
          resolve(false);
        }
      }, 1000);
    });
  }
  
  /**
   * Verify a recurring donation token
   * This checks if the subscription is still active
   */
  private async verifyRecurringToken(): Promise<void> {
    if (!this.state.recurringToken) {
      return;
    }
    
    try {
      // Note: This verification is anonymous
      // The token doesn't identify the user, just the subscription
      const response = await fetch(`${DONATION_API_URL}/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: this.state.recurringToken })
      });
      
      const data = await response.json();
      
      if (!data.active) {
        // Subscription is no longer active
        this.state.recurringActive = false;
        this.state.recurringToken = undefined;
        this.saveState();
      }
    } catch (e) {
      console.error('Failed to verify recurring token', e);
      // Don't change state on error, try again next time
    }
  }
  
  /**
   * Permanently disable donation prompts
   */
  private disablePrompts(): void {
    this.state.promptDisabled = true;
    this.saveState();
  }
}

// Styles for the donation modal
const addDonationStyles = (): void => {
  const style = document.createElement('style');
  style.textContent = `
    .shini-donation-modal {
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background-color: rgba(0, 0, 0, 0.7);
      z-index: 10000;
      display: flex;
      justify-content: center;
      align-items: center;
    }
    
    .shini-donation-content {
      background-color: #fff;
      color: #333;
      padding: 20px;
      border-radius: 8px;
      max-width: 500px;
      width: 90%;
    }
    
    .shini-donation-buttons {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin: 20px 0;
    }
    
    .shini-donation-buttons button {
      padding: 10px 15px;
      border-radius: 4px;
      border: none;
      cursor: pointer;
    }
    
    #shini-donate-one-time, #shini-donate-recurring {
      background-color: #4CAF50;
      color: white;
    }
    
    #shini-donate-later {
      background-color: #f1f1f1;
      color: #333;
    }
    
    #shini-donate-never {
      background-color: transparent;
      color: #777;
      text-decoration: underline;
    }
    
    .shini-privacy-notice {
      font-size: 0.8em;
      color: #777;
      margin-top: 20px;
    }
    
    /* Dark theme support */
    @media (prefers-color-scheme: dark) {
      .shini-donation-content {
        background-color: #333;
        color: #f1f1f1;
      }
      
      #shini-donate-later {
        background-color: #555;
        color: #f1f1f1;
      }
      
      #shini-donate-never {
        color: #aaa;
      }
      
      .shini-privacy-notice {
        color: #aaa;
      }
    }
  `;
  
  document.head.appendChild(style);
};

// Initialize donation manager and styles when needed
export const initDonationSystem = (): DonationManager => {
  addDonationStyles();
  return new DonationManager();
};
