/**
 * Configuration system for Enhanced Shinigami Eyes
 * 
 * This module handles user configuration options, including backend settings,
 * enhancement features, and privacy controls.
 */

import { DonationManager } from './donation';

// Backend modes available to users
export enum BackendMode {
  LEGACY = 'legacy',      // Original Shinigami Eyes without ML enhancements
  LOCAL = 'local',        // Enhanced features using local backend
  HOSTED = 'hosted'       // Enhanced features using hosted backend
}

// Feature toggles for ML enhancements
export interface EnhancementFeatures {
  contentAnalysis: boolean;   // Analyze text content for classification
  profileAnalysis: boolean;   // Analyze social media profiles
  websiteAnalysis: boolean;   // Analyze linked websites via Common Crawl
  grayAreaLabeling: boolean;  // Enable "gray area" classifications
  confidenceDisplay: boolean; // Show confidence levels for classifications
}

// Main configuration interface
export interface ShiniConfig {
  // Backend configuration
  backendMode: BackendMode;
  localBackendUrl: string;
  hostedBackendUrl: string;
  
  // Feature toggles
  enhancementFeatures: EnhancementFeatures;
  
  // Privacy and security
  sendAnonymousStats: boolean;  // Send anonymous usage statistics
  
  // UI settings
  darkThemeColors: {
    transFriendly: string;
    transphobic: string;
    grayArea: string;
  };
  lightThemeColors: {
    transFriendly: string;
    transphobic: string;
    grayArea: string;
  };
}

// Default configuration values
const DEFAULT_CONFIG: ShiniConfig = {
  backendMode: BackendMode.LEGACY,
  localBackendUrl: 'http://localhost:5000',
  hostedBackendUrl: 'https://api.shini-eyes-enhanced.org',
  
  enhancementFeatures: {
    contentAnalysis: true,
    profileAnalysis: true,
    websiteAnalysis: true,
    grayAreaLabeling: true,
    confidenceDisplay: true
  },
  
  sendAnonymousStats: false,
  
  darkThemeColors: {
    transFriendly: '#0C8',
    transphobic: '#F30',
    grayArea: '#F80'
  },
  
  lightThemeColors: {
    transFriendly: '#0C8',
    transphobic: '#F30',
    grayArea: '#F80'
  }
};

/**
 * Configuration Manager
 * 
 * Handles loading, saving, and accessing configuration settings
 */
export class ConfigManager {
  private config: ShiniConfig;
  private donationManager: DonationManager;
  
  constructor() {
    this.config = this.loadConfig();
    this.donationManager = new DonationManager();
  }
  
  /**
   * Load configuration from storage
   */
  private loadConfig(): ShiniConfig {
    try {
      const storedConfig = localStorage.getItem('shini_config');
      if (storedConfig) {
        // Merge stored config with default config to ensure all fields exist
        return { ...DEFAULT_CONFIG, ...JSON.parse(storedConfig) };
      }
    } catch (e) {
      console.error('Failed to load configuration', e);
    }
    
    return { ...DEFAULT_CONFIG };
  }
  
  /**
   * Save configuration to storage
   */
  private saveConfig(): void {
    try {
      localStorage.setItem('shini_config', JSON.stringify(this.config));
    } catch (e) {
      console.error('Failed to save configuration', e);
    }
  }
  
  /**
   * Get the current configuration
   */
  getConfig(): ShiniConfig {
    return { ...this.config };
  }
  
  /**
   * Update configuration with new values
   */
  updateConfig(newConfig: Partial<ShiniConfig>): void {
    // Deep merge the new config with the current config
    this.config = this.deepMerge(this.config, newConfig);
    this.saveConfig();
    
    // Check if we should show donation prompt
    this.checkDonationPrompt();
  }
  
  /**
   * Deep merge two objects
   */
  private deepMerge<T>(target: T, source: Partial<T>): T {
    const output = { ...target };
    
    if (isObject(target) && isObject(source)) {
      Object.keys(source).forEach(key => {
        if (isObject(source[key])) {
          if (!(key in target)) {
            Object.assign(output, { [key]: source[key] });
          } else {
            output[key] = this.deepMerge(target[key], source[key]);
          }
        } else {
          Object.assign(output, { [key]: source[key] });
        }
      });
    }
    
    return output;
  }
  
  /**
   * Get active backend URL based on current mode
   */
  getActiveBackendUrl(): string {
    switch (this.config.backendMode) {
      case BackendMode.LOCAL:
        return this.config.localBackendUrl;
      case BackendMode.HOSTED:
        return this.config.hostedBackendUrl;
      default:
        return '';
    }
  }
  
  /**
   * Check if enhanced features are enabled
   */
  isEnhancedMode(): boolean {
    return this.config.backendMode === BackendMode.LOCAL || 
           this.config.backendMode === BackendMode.HOSTED;
  }
  
  /**
   * Check if a specific enhancement feature is enabled
   */
  isFeatureEnabled(feature: keyof EnhancementFeatures): boolean {
    return this.isEnhancedMode() && this.config.enhancementFeatures[feature];
  }
  
  /**
   * Check if we should show donation prompt
   */
  private checkDonationPrompt(): void {
    // Only show donation prompt for hosted backend users
    if (this.config.backendMode === BackendMode.HOSTED && 
        this.donationManager.shouldShowPrompt()) {
      this.donationManager.showDonationPrompt();
    }
  }
}

// Helper function to check if a value is an object
function isObject(item: any): item is Record<string, any> {
  return (item && typeof item === 'object' && !Array.isArray(item));
}

// Create and export singleton instance
const configManager = new ConfigManager();
export default configManager;
