#!/usr/bin/env python3
"""
Donation verification API for Enhanced Shinigami Eyes.

This module handles verifying Stripe recurring donations without storing user data.
All verification is done using anonymous tokens that don't identify users.
"""

import os
import logging
import json
import time
from typing import Dict, Any, Optional
import secrets
import hashlib
import stripe
from flask import Blueprint, request, jsonify

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Blueprint
donation_bp = Blueprint('donation_api', __name__)

# Get Stripe API key from environment
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', 'sk_test_YOUR_TEST_KEY')
stripe.api_key = STRIPE_SECRET_KEY

# Token to subscription mapping (in-memory only, not persisted)
# This maps anonymous tokens to Stripe subscription IDs
# Format: {token_hash: {'subscription_id': 'sub_xxx', 'expires': timestamp}}
token_cache = {}

# Cache expiry (12 hours)
CACHE_EXPIRY = 12 * 60 * 60


@donation_bp.route('/donate/create-session', methods=['POST'])
def create_checkout_session():
    """Create a new Stripe checkout session."""
    try:
        data = request.json
        
        if not data or 'type' not in data:
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Get the donation type (one-time or recurring)
        donation_type = data.get('type', 'one-time')
        
        # Generate a session ID
        session_id = secrets.token_hex(16)
        
        # Create Stripe session
        if donation_type == 'recurring':
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': 'Enhanced Shinigami Eyes Monthly Support',
                            'description': 'Monthly support for Enhanced Shinigami Eyes server costs',
                        },
                        'unit_amount': 500,  # $5.00
                        'recurring': {
                            'interval': 'month',
                        },
                    },
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=f'https://api.shini-eyes-enhanced.org/donation/success?session_id={session_id}&type=recurring',
                cancel_url='https://api.shini-eyes-enhanced.org/donation/cancel',
                client_reference_id=session_id,
                metadata={
                    'type': 'recurring',
                    'session_id': session_id
                }
            )
        else:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': 'Enhanced Shinigami Eyes Donation',
                            'description': 'One-time donation to support Enhanced Shinigami Eyes',
                        },
                        'unit_amount': 500,  # $5.00
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=f'https://api.shini-eyes-enhanced.org/donation/success?session_id={session_id}&type=one-time',
                cancel_url='https://api.shini-eyes-enhanced.org/donation/cancel',
                client_reference_id=session_id,
                metadata={
                    'type': 'one-time',
                    'session_id': session_id
                }
            )
        
        return jsonify({
            'session_id': session.id,
            'url': session.url
        })
        
    except Exception as e:
        logger.error(f"Error creating checkout session: {str(e)}")
        return jsonify({'error': 'Failed to create checkout session'}), 500


@donation_bp.route('/donation/success', methods=['GET'])
def donation_success():
    """Handle successful donation and generate token for recurring donations."""
    try:
        session_id = request.args.get('session_id')
        donation_type = request.args.get('type', 'one-time')
        
        if not session_id:
            return "Invalid request", 400
        
        # For recurring donations, generate a token
        if donation_type == 'recurring':
            # Get Stripe session to verify it's legitimate
            try:
                # Look up the session using the client_reference_id
                sessions = stripe.checkout.Session.list(
                    limit=1,
                    client_reference_id=session_id
                )
                
                if not sessions or not sessions.data:
                    return "Session not found", 404
                
                session = sessions.data[0]
                
                # Get the subscription ID
                subscription_id = session.subscription
                
                if not subscription_id:
                    return "No subscription found", 400
                
                # Generate a unique token for this subscription
                token = secrets.token_hex(32)
                token_hash = hashlib.sha256(token.encode()).hexdigest()
                
                # Store a mapping of token hash to subscription ID (privacy-preserving)
                token_cache[token_hash] = {
                    'subscription_id': subscription_id,
                    'expires': time.time() + CACHE_EXPIRY
                }
                
                # Return success page with token
                # This token will be sent to the extension via postMessage
                html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Thank You for Your Support!</title>
                    <script>
                        // Send the token back to the extension
                        window.addEventListener('DOMContentLoaded', function() {{
                            if (window.opener) {{
                                window.opener.postMessage({{
                                    type: 'donation_complete',
                                    recurringToken: '{token}'
                                }}, '*');
                                
                                // Close automatically after 5 seconds
                                setTimeout(function() {{
                                    window.close();
                                }}, 5000);
                            }}
                        }});
                    </script>
                    <style>
                        body {{
                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
                            max-width: 600px;
                            margin: 0 auto;
                            padding: 20px;
                            text-align: center;
                        }}
                        h1 {{
                            color: #4CAF50;
                        }}
                    </style>
                </head>
                <body>
                    <h1>Thank You for Your Support!</h1>
                    <p>Your monthly contribution helps keep Enhanced Shinigami Eyes running for everyone.</p>
                    <p>This window will close automatically.</p>
                </body>
                </html>
                """
                
                return html
                
            except Exception as e:
                logger.error(f"Error processing donation success: {str(e)}")
                return "An error occurred", 500
        else:
            # For one-time donations, just show a thank you page
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Thank You for Your Support!</title>
                <script>
                    // Notify the extension
                    window.addEventListener('DOMContentLoaded', function() {
                        if (window.opener) {
                            window.opener.postMessage({
                                type: 'donation_complete'
                            }, '*');
                            
                            // Close automatically after 5 seconds
                            setTimeout(function() {
                                window.close();
                            }, 5000);
                        }
                    });
                </script>
                <style>
                    body {
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
                        max-width: 600px;
                        margin: 0 auto;
                        padding: 20px;
                        text-align: center;
                    }
                    h1 {
                        color: #4CAF50;
                    }
                </style>
            </head>
            <body>
                <h1>Thank You for Your Support!</h1>
                <p>Your donation helps keep Enhanced Shinigami Eyes running for everyone.</p>
                <p>This window will close automatically.</p>
            </body>
            </html>
            """
            
            return html
            
    except Exception as e:
        logger.error(f"Error processing donation success: {str(e)}")
        return "An error occurred", 500


@donation_bp.route('/donation/cancel', methods=['GET'])
def donation_cancel():
    """Handle cancelled donation."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Donation Cancelled</title>
        <script>
            // Notify the extension
            window.addEventListener('DOMContentLoaded', function() {
                if (window.opener) {
                    window.opener.postMessage({
                        type: 'donation_cancelled'
                    }, '*');
                    
                    // Close automatically after 3 seconds
                    setTimeout(function() {
                        window.close();
                    }, 3000);
                }
            });
        </script>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
                text-align: center;
            }
        </style>
    </head>
    <body>
        <h1>Donation Cancelled</h1>
        <p>No problem. You can still use all features of Enhanced Shinigami Eyes.</p>
        <p>This window will close automatically.</p>
    </body>
    </html>
    """
    
    return html


@donation_bp.route('/verify', methods=['POST'])
def verify_token():
    """Verify if a recurring donation is still active."""
    try:
        data = request.json
        
        if not data or 'token' not in data:
            return jsonify({'error': 'Missing token'}), 400
        
        token = data['token']
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # Check if token is in cache
        cached = token_cache.get(token_hash)
        if cached and cached['expires'] > time.time():
            # Token found in cache, return cached result
            subscription_id = cached['subscription_id']
        else:
            # Token not found in cache, must be invalid
            return jsonify({'active': False}), 200
        
        # Verify subscription with Stripe
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            
            # Check if subscription is active
            active = subscription.status == 'active'
            
            # Update cache
            if active:
                token_cache[token_hash] = {
                    'subscription_id': subscription_id,
                    'expires': time.time() + CACHE_EXPIRY
                }
            else:
                # Remove from cache if not active
                if token_hash in token_cache:
                    del token_cache[token_hash]
            
            return jsonify({'active': active})
            
        except stripe.error.StripeError:
            # Subscription not found or other Stripe error
            if token_hash in token_cache:
                del token_cache[token_hash]
            return jsonify({'active': False}), 200
        
    except Exception as e:
        logger.error(f"Error verifying token: {str(e)}")
        return jsonify({'error': 'Failed to verify token'}), 500


# Cleanup expired tokens
def cleanup_token_cache():
    """Remove expired tokens from cache."""
    current_time = time.time()
    expired = [token for token, data in token_cache.items() if data['expires'] < current_time]
    
    for token in expired:
        del token_cache[token]
    
    return len(expired)


# Webhook for Stripe events
@donation_bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events."""
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        # Invalid payload
        logger.error(f"Invalid Stripe payload: {str(e)}")
        return "Invalid payload", 400
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        logger.error(f"Invalid Stripe signature: {str(e)}")
        return "Invalid signature", 400
    
    # Handle specific events
    if event['type'] == 'customer.subscription.deleted':
        # Subscription was cancelled
        subscription_id = event['data']['object']['id']
        
        # Find and remove token for this subscription
        to_remove = []
        for token, data in token_cache.items():
            if data['subscription_id'] == subscription_id:
                to_remove.append(token)
        
        for token in to_remove:
            del token_cache[token]
    
    return jsonify({'status': 'success'})
