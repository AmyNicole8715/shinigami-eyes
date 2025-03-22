#!/usr/bin/env python3
"""
Main Flask application for Shinigami Eyes ML service.
This service provides content analysis for the Shinigami Eyes browser extension.
Designed to run as a hosted service that respects user privacy.
"""

import os
import json
import logging
from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import spacy
import torch
import threading
import time
import uuid

from utils.content_analyzer import ContentAnalyzer
from utils.web_analyzer import WebAnalyzer
from utils.common_crawl import CommonCrawlAnalyzer
from donation_api import donation_bp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ml_service.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Register donation blueprint
app.register_blueprint(donation_bp, url_prefix='/donation')

# Enable CORS for browser extension
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    return response

# Initialize analyzers
content_analyzer = ContentAnalyzer()
web_analyzer = WebAnalyzer()
cc_analyzer = CommonCrawlAnalyzer()

# In-memory cache for recently analyzed content
analysis_cache = {}
CACHE_EXPIRY = 24 * 60 * 60  # 24 hours in seconds

# Anonymous usage stats (only counts, no identifiable info)
request_stats = {
    'analyze_text': 0,
    'analyze_profile': 0,
    'analyze_url': 0,
    'verify_submission': 0,
    'total': 0,
}

# Rate limiting to prevent abuse
rate_limit_cache = {}  # IP -> {timestamp, count}
RATE_LIMIT_WINDOW = 60  # 1 minute
RATE_LIMIT_MAX = 60  # 60 requests per minute

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'analyzers': {
            'content': content_analyzer.status(),
            'web': web_analyzer.status(),
            'common_crawl': cc_analyzer.status()
        },
        'stats': {
            'requests': request_stats,
            'cache_size': len(analysis_cache)
        },
        'version': '1.0.0'
    })

@app.route('/analyze/text', methods=['POST'])
def analyze_text():
    """Analyze text content and return classification."""
    data = request.json
    if not data or 'text' not in data:
        return jsonify({'error': 'No text provided'}), 400
    
    text = data['text']
    cache_key = f"text:{hash(text)}"
    
    # Check cache first
    if cache_key in analysis_cache:
        return jsonify(analysis_cache[cache_key])
    
    # Perform analysis
    result = content_analyzer.analyze_text(text)
    
    # Cache result
    analysis_cache[cache_key] = result
    
    return jsonify(result)

@app.route('/analyze/profile', methods=['POST'])
def analyze_profile():
    """Analyze a social media profile based on recent posts."""
    data = request.json
    if not data or 'identifier' not in data or 'platform' not in data:
        return jsonify({'error': 'Missing identifier or platform'}), 400
    
    identifier = data['identifier']
    platform = data['platform']
    
    cache_key = f"profile:{platform}:{identifier}"
    
    # Check cache first
    if cache_key in analysis_cache:
        # Only use cache if it's fresh (less than a day old)
        if analysis_cache[cache_key].get('timestamp', 0) > time.time() - CACHE_EXPIRY:
            return jsonify(analysis_cache[cache_key])
    
    # Fetch and analyze profile
    try:
        profile_data = web_analyzer.fetch_profile_data(identifier, platform)
        if not profile_data or not profile_data.get('posts', []):
            return jsonify({
                'error': 'Could not fetch sufficient data from profile',
                'classification': 1,  # Gray area due to lack of data
                'confidence': 0.1
            }), 200
        
        result = content_analyzer.analyze_profile(profile_data['posts'])
        
        # Add common crawl analysis if website links are present
        if profile_data.get('links', []):
            cc_results = cc_analyzer.analyze_links(profile_data['links'])
            result['linked_sites_analysis'] = cc_results
            
            # Adjust classification based on linked sites if confidence is low
            if result['confidence'] < 0.6 and cc_results['confidence'] > 0.7:
                result['classification'] = cc_results['classification']
                result['confidence'] = (result['confidence'] + cc_results['confidence']) / 2
                result['classification_adjusted_by'] = 'linked_sites'
        
        # Add timestamp for cache expiration
        result['timestamp'] = time.time()
        
        # Cache result
        analysis_cache[cache_key] = result
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error analyzing profile {platform}:{identifier} - {str(e)}")
        return jsonify({
            'error': f"Analysis failed: {str(e)}",
            'classification': 1,  # Gray area due to error
            'confidence': 0.1
        }), 500

@app.route('/analyze/url', methods=['POST'])
def analyze_url():
    """Analyze content from a URL."""
    data = request.json
    if not data or 'url' not in data:
        return jsonify({'error': 'No URL provided'}), 400
    
    url = data['url']
    cache_key = f"url:{url}"
    
    # Check cache first
    if cache_key in analysis_cache:
        return jsonify(analysis_cache[cache_key])
    
    # Fetch and analyze URL content
    try:
        content = web_analyzer.fetch_url_content(url)
        if not content:
            return jsonify({
                'error': 'Could not fetch content from URL',
                'classification': 1,  # Gray area due to lack of data
                'confidence': 0.1
            }), 200
        
        result = content_analyzer.analyze_text(content)
        
        # Add common crawl analysis if available
        cc_result = cc_analyzer.analyze_single_url(url)
        if cc_result:
            result['common_crawl_analysis'] = cc_result
            
            # Adjust classification if common crawl has high confidence
            if result['confidence'] < 0.6 and cc_result.get('confidence', 0) > 0.7:
                result['classification'] = cc_result.get('classification', result['classification'])
                result['confidence'] = (result['confidence'] + cc_result.get('confidence', 0)) / 2
                result['classification_adjusted_by'] = 'common_crawl'
        
        # Cache result
        analysis_cache[cache_key] = result
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error analyzing URL {url} - {str(e)}")
        return jsonify({
            'error': f"Analysis failed: {str(e)}",
            'classification': 1,  # Gray area due to error
            'confidence': 0.1
        }), 500

@app.route('/verify/submission', methods=['POST'])
def verify_submission():
    """Verify a user submission for marking an identifier."""
    data = request.json
    if not data or 'identifier' not in data or 'proposed_label' not in data:
        return jsonify({'error': 'Missing identifier or proposed label'}), 400
    
    identifier = data['identifier']
    proposed_label = data['proposed_label']
    platform = data.get('platform', 'unknown')
    
    # Check if this is a known bad identifier
    if web_analyzer.is_bad_identifier(identifier):
        return jsonify({
            'verified': False,
            'reason': 'bad_identifier',
            'recommendation': 'reject'
        })
    
    # Analyze the profile
    try:
        profile_data = web_analyzer.fetch_profile_data(identifier, platform)
        if not profile_data or not profile_data.get('posts', []):
            return jsonify({
                'verified': False,
                'confidence': 0.1,
                'reason': 'insufficient_data',
                'recommendation': 'gray_area'
            })
        
        result = content_analyzer.analyze_profile(profile_data['posts'])
        
        # Map classification to label
        label_map = {
            0: 't-friendly',
            1: 'gray-area',
            2: 'transphobic'
        }
        
        recommended_label = label_map.get(result['classification'], 'gray-area')
        
        # Compare with proposed label
        verification = {
            'verified': recommended_label == proposed_label,
            'confidence': result['confidence'],
            'ml_recommended_label': recommended_label
        }
        
        # If high confidence contradiction, recommend rejecting
        if not verification['verified'] and result['confidence'] > 0.8:
            verification['recommendation'] = 'reject'
        # If medium confidence contradiction, recommend gray area
        elif not verification['verified'] and result['confidence'] > 0.5:
            verification['recommendation'] = 'gray_area'
        # If low confidence, accept user judgment
        else:
            verification['recommendation'] = 'accept'
            
        return jsonify(verification)
        
    except Exception as e:
        logger.error(f"Error verifying submission for {platform}:{identifier} - {str(e)}")
        return jsonify({
            'verified': False,
            'reason': f"verification_error: {str(e)}",
            'recommendation': 'gray_area'
        }), 500

def clear_expired_cache():
    """Clear expired items from cache periodically."""
    while True:
        current_time = time.time()
        expired_keys = []
        
        # Find expired keys
        for key, value in analysis_cache.items():
            if value.get('timestamp', 0) < current_time - CACHE_EXPIRY:
                expired_keys.append(key)
        
        # Remove expired keys
        for key in expired_keys:
            del analysis_cache[key]
        
        logger.info(f"Cache cleanup: removed {len(expired_keys)} expired entries")
        
        # Sleep for 6 hours
        time.sleep(6 * 60 * 60)

# Apply rate limiting to specific routes
def rate_limit():
    """Apply rate limiting to prevent abuse."""
    # Get IP (in production, get from X-Forwarded-For with proper validation)
    ip = request.remote_addr
    
    # Generate a temporary ID if IP is not available (development)
    if not ip or ip == '127.0.0.1':
        # For local testing, we still want some kind of rate limiting
        # Use a random ID that persists only for this process
        ip = request.headers.get('X-Client-ID', str(uuid.uuid4()))
    
    now = time.time()
    
    # Initialize or update rate limit entry
    if ip not in rate_limit_cache:
        rate_limit_cache[ip] = {'timestamp': now, 'count': 1}
        return None
    
    # Check if we're in a new time window
    if now - rate_limit_cache[ip]['timestamp'] > RATE_LIMIT_WINDOW:
        rate_limit_cache[ip] = {'timestamp': now, 'count': 1}
        return None
    
    # Increment count
    rate_limit_cache[ip]['count'] += 1
    
    # Check if over limit
    if rate_limit_cache[ip]['count'] > RATE_LIMIT_MAX:
        return jsonify({
            'error': 'Rate limit exceeded',
            'retry_after': int(RATE_LIMIT_WINDOW - (now - rate_limit_cache[ip]['timestamp']))
        }), 429
    
    return None

# Apply rate limiting to endpoints
for endpoint in ['/analyze/text', '/analyze/profile', '/analyze/url', '/verify/submission']:
    app.before_request_funcs.setdefault(None, []).append(rate_limit)

# Clean rate limit cache periodically
def clear_expired_rate_limits():
    """Clear expired rate limit entries."""
    while True:
        time.sleep(RATE_LIMIT_WINDOW * 2)
        
        now = time.time()
        expired = [ip for ip, data in rate_limit_cache.items() 
                  if now - data['timestamp'] > RATE_LIMIT_WINDOW]
        
        for ip in expired:
            del rate_limit_cache[ip]
        
        logger.info(f"Cleared {len(expired)} expired rate limit entries")

if __name__ == '__main__':
    # Start cache cleanup thread
    cleanup_thread = threading.Thread(target=clear_expired_cache, daemon=True)
    cleanup_thread.start()
    
    # Start rate limit cleanup thread
    rate_limit_thread = threading.Thread(target=clear_expired_rate_limits, daemon=True)
    rate_limit_thread.start()
    
    # Start the server (gunicorn will be used in production)
    app.run(host='0.0.0.0', port=5000, debug=True)
