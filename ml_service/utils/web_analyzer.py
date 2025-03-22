#!/usr/bin/env python3
"""
Web Analyzer for Shinigami Eyes ML service.
Fetches and analyzes content from various platforms.
"""

import os
import logging
import json
import re
import time
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class WebAnalyzer:
    """Fetches and analyzes web content from various platforms."""
    
    def __init__(self):
        """Initialize the web analyzer."""
        # User agent to mimic browser
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        
        # Load bad identifiers from extension (if available)
        self.bad_identifiers = self._load_bad_identifiers()
        
        # Platform-specific fetchers
        self.platform_fetchers = {
            "twitter": self._fetch_twitter_data,
            "facebook": self._fetch_facebook_data,
            "reddit": self._fetch_reddit_data,
            "youtube": self._fetch_youtube_data,
            "mastodon": self._fetch_mastodon_data,
            "medium": self._fetch_medium_data,
            "bsky": self._fetch_bsky_data,
            "unknown": self._fetch_generic_data
        }
        
        # Request cache to avoid hammering services
        self.request_cache = {}
        self.cache_expiry = 60 * 60  # 1 hour in seconds
    
    def status(self) -> Dict[str, Any]:
        """Return the status of the analyzer."""
        return {
            "platforms_supported": list(self.platform_fetchers.keys()),
            "bad_identifiers_loaded": len(self.bad_identifiers) > 0
        }
    
    def _load_bad_identifiers(self) -> Dict[str, bool]:
        """Load bad identifiers from the extension configuration."""
        bad_identifiers = {}
        try:
            # Try to load from extension directory
            path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                               "extension", "background.ts")
            
            if os.path.exists(path):
                with open(path, 'r') as f:
                    content = f.read()
                    
                # Extract bad identifiers array
                match = re.search(r'const badIdentifiersArray = \[(.*?)\]', content, re.DOTALL)
                if match:
                    identifiers_text = match.group(1)
                    # Extract quoted strings
                    identifiers = re.findall(r"'([^']*)'", identifiers_text)
                    if not identifiers:
                        identifiers = re.findall(r'"([^"]*)"', identifiers_text)
                    
                    # Process identifiers (strip the =XX suffix)
                    for identifier in identifiers:
                        parts = identifier.split('=')
                        bad_identifiers[parts[0]] = True
            
            logger.info(f"Loaded {len(bad_identifiers)} bad identifiers from extension")
            
        except Exception as e:
            logger.error(f"Failed to load bad identifiers: {str(e)}")
            
            # Add some common bad identifiers as fallback
            bad_ids = ["facebook.com", "twitter.com", "reddit.com", "youtube.com", 
                     "change.org", "google.com", "instagram.com"]
            
            for bad_id in bad_ids:
                bad_identifiers[bad_id] = True
                
        return bad_identifiers
    
    def is_bad_identifier(self, identifier: str) -> bool:
        """Check if an identifier is in the bad identifiers list."""
        # Extract domain from identifier if it contains a URL
        if '/' in identifier:
            parsed = urlparse(identifier if identifier.startswith('http') else f"https://{identifier}")
            domain = parsed.netloc
            if domain.startswith('www.'):
                domain = domain[4:]
            
            return domain in self.bad_identifiers
            
        # Check direct match
        return identifier in self.bad_identifiers
    
    def _cached_request(self, url: str, headers: Optional[Dict[str, str]] = None) -> Optional[requests.Response]:
        """Make a request with caching to avoid hammering servers."""
        now = time.time()
        
        # Check cache
        if url in self.request_cache:
            cache_time, response = self.request_cache[url]
            if now - cache_time < self.cache_expiry:
                return response
        
        # Make new request
        if not headers:
            headers = {'User-Agent': self.user_agent}
            
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                self.request_cache[url] = (now, response)
                return response
            
            logger.warning(f"Request to {url} failed with status {response.status_code}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {str(e)}")
            return None
    
    def fetch_url_content(self, url: str) -> Optional[str]:
        """Fetch content from a URL."""
        response = self._cached_request(url)
        if not response:
            return None
        
        try:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.extract()
            
            # Extract text content
            text = soup.get_text(separator=' ')
            
            # Clean up text
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return text
            
        except Exception as e:
            logger.error(f"Failed to parse content from {url}: {str(e)}")
            return None
    
    def _extract_links_from_html(self, html: str) -> List[str]:
        """Extract links from HTML content."""
        links = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.startswith('http'):
                    links.append(href)
        except Exception as e:
            logger.error(f"Failed to extract links: {str(e)}")
        
        return links
    
    def _fetch_twitter_data(self, identifier: str) -> Dict[str, Any]:
        """Fetch data from Twitter/X."""
        # Note: Twitter requires authentication for API access
        # This is a simplified version that uses public web scraping
        # In production, you'd use Twitter API with proper authentication
        
        # Clean identifier
        if '/' in identifier:
            username = identifier.split('/')[-1]
        else:
            username = identifier
        
        if username.startswith('@'):
            username = username[1:]
        
        url = f"https://nitter.net/{username}"
        
        response = self._cached_request(url)
        if not response:
            return {"error": "Failed to fetch Twitter data"}
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract posts
        posts = []
        for tweet in soup.select('.tweet-content'):
            posts.append(tweet.get_text(strip=True))
        
        # Extract links
        links = []
        for link in soup.select('.tweet-link'):
            href = link.get('href')
            if href and href.startswith('http'):
                links.append(href)
        
        return {
            "posts": posts[:20],  # Limit to 20 posts
            "links": links,
            "platform": "twitter"
        }
    
    def _fetch_reddit_data(self, identifier: str) -> Dict[str, Any]:
        """Fetch data from Reddit."""
        # Clean identifier
        if identifier.startswith('reddit.com/'):
            path = identifier.split('reddit.com/')[-1]
        else:
            path = identifier
        
        # Determine if it's a user or subreddit
        if path.startswith('u/') or path.startswith('user/'):
            username = path.split('/')[-1]
            url = f"https://www.reddit.com/user/{username}.json"
        elif path.startswith('r/'):
            subreddit = path.split('/')[-1]
            url = f"https://www.reddit.com/r/{subreddit}.json"
        else:
            return {"error": "Invalid Reddit identifier"}
        
        # Use Reddit JSON API
        headers = {
            'User-Agent': 'Shinigami Eyes Content Analyzer/1.0'
        }
        
        response = self._cached_request(url, headers)
        if not response:
            return {"error": "Failed to fetch Reddit data"}
        
        try:
            data = response.json()
            posts = []
            links = []
            
            # Extract posts from response
            if 'data' in data and 'children' in data['data']:
                for child in data['data']['children']:
                    if 'data' in child:
                        post_data = child['data']
                        
                        # Get post content
                        if 'selftext' in post_data and post_data['selftext']:
                            posts.append(post_data['selftext'])
                        elif 'body' in post_data and post_data['body']:
                            posts.append(post_data['body'])
                        
                        # Get title if available
                        if 'title' in post_data and post_data['title']:
                            posts.append(post_data['title'])
                        
                        # Get links
                        if 'url' in post_data and post_data['url'].startswith('http'):
                            links.append(post_data['url'])
            
            return {
                "posts": posts[:20],  # Limit to 20 posts
                "links": links,
                "platform": "reddit"
            }
            
        except Exception as e:
            logger.error(f"Failed to parse Reddit data: {str(e)}")
            return {"error": "Failed to parse Reddit data"}
    
    def _fetch_facebook_data(self, identifier: str) -> Dict[str, Any]:
        """Fetch data from Facebook."""
        # Note: Facebook severely restricts scraping
        # This is a placeholder - in production, you'd need Facebook Graph API with proper permissions
        return {
            "posts": [],
            "links": [],
            "platform": "facebook",
            "error": "Facebook data fetching requires API access"
        }
    
    def _fetch_youtube_data(self, identifier: str) -> Dict[str, Any]:
        """Fetch data from YouTube."""
        # Clean identifier
        if '/' in identifier:
            parts = identifier.split('/')
            if 'channel' in identifier:
                channel_id = parts[-1]
                url = f"https://www.youtube.com/channel/{channel_id}/videos"
            elif 'user' in identifier:
                username = parts[-1]
                url = f"https://www.youtube.com/user/{username}/videos"
            else:
                return {"error": "Invalid YouTube identifier"}
        else:
            url = f"https://www.youtube.com/user/{identifier}/videos"
        
        response = self._cached_request(url)
        if not response:
            return {"error": "Failed to fetch YouTube data"}
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract video titles as posts
        posts = []
        for title_element in soup.select('a#video-title'):
            title = title_element.get('title')
            if title:
                posts.append(title)
        
        # Extract channel description if available
        about_url = url.replace('/videos', '/about')
        about_response = self._cached_request(about_url)
        if about_response:
            about_soup = BeautifulSoup(about_response.content, 'html.parser')
            description = about_soup.select_one('yt-formatted-string#description')
            if description:
                posts.append(description.get_text())
        
        return {
            "posts": posts[:20],
            "links": [],  # YouTube doesn't typically have external links in videos
            "platform": "youtube"
        }
    
    def _fetch_mastodon_data(self, identifier: str) -> Dict[str, Any]:
        """Fetch data from Mastodon."""
        # Mastodon is federated, so this is complex
        # This is a simplified version for a single instance
        
        # Parse identifier to get instance and username
        if '@' in identifier:
            parts = identifier.split('@')
            username = parts[0].strip('@')
            instance = parts[-1]
        elif '/' in identifier:
            parts = identifier.split('/')
            instance = parts[0].split('://')[1] if '://' in parts[0] else parts[0]
            username = parts[-1]
        else:
            return {"error": "Invalid Mastodon identifier"}
        
        # Try to fetch public profile via RSS
        url = f"https://{instance}/@{username}.rss"
        
        response = self._cached_request(url)
        if not response:
            return {"error": "Failed to fetch Mastodon data"}
        
        try:
            soup = BeautifulSoup(response.content, 'xml')
            
            posts = []
            for item in soup.find_all('item'):
                description = item.find('description')
                if description:
                    posts.append(description.get_text())
            
            return {
                "posts": posts[:20],
                "links": [],
                "platform": "mastodon"
            }
            
        except Exception as e:
            logger.error(f"Failed to parse Mastodon data: {str(e)}")
            return {"error": "Failed to parse Mastodon data"}
    
    def _fetch_medium_data(self, identifier: str) -> Dict[str, Any]:
        """Fetch data from Medium."""
        # Clean identifier
        if '/' in identifier:
            username = identifier.split('/')[-1]
        else:
            username = identifier
        
        url = f"https://medium.com/@{username}"
        
        response = self._cached_request(url)
        if not response:
            return {"error": "Failed to fetch Medium data"}
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract article titles and content
        posts = []
        for article in soup.select('article'):
            title = article.select_one('h2')
            if title:
                posts.append(title.get_text())
            
            content = article.select_one('p')
            if content:
                posts.append(content.get_text())
        
        return {
            "posts": posts[:20],
            "links": self._extract_links_from_html(response.text),
            "platform": "medium"
        }
    
    def _fetch_bsky_data(self, identifier: str) -> Dict[str, Any]:
        """Fetch data from BlueSky."""
        # Clean identifier
        if '/' in identifier:
            username = identifier.split('/')[-1]
        else:
            username = identifier
        
        url = f"https://bsky.app/profile/{username}"
        
        response = self._cached_request(url)
        if not response:
            return {"error": "Failed to fetch BlueSky data"}
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract posts (this is simplified and might need adjustment as BlueSky changes)
        posts = []
        for post_element in soup.select('.post-content'):
            posts.append(post_element.get_text())
        
        links = self._extract_links_from_html(response.text)
        
        return {
            "posts": posts[:20],
            "links": links,
            "platform": "bsky"
        }
    
    def _fetch_generic_data(self, identifier: str) -> Dict[str, Any]:
        """Fetch data from an unknown platform."""
        # Assume identifier is a URL
        if not identifier.startswith('http'):
            identifier = f"https://{identifier}"
        
        response = self._cached_request(identifier)
        if not response:
            return {"error": "Failed to fetch data from URL"}
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract text content
        for script in soup(["script", "style"]):
            script.extract()
        
        text = soup.get_text(separator=' ')
        
        # Clean up text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        # Split into chunks to simulate "posts"
        chunks = []
        current_chunk = ""
        
        for paragraph in text.split('\n'):
            if len(current_chunk) + len(paragraph) < 2000:
                current_chunk += paragraph + " "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = paragraph + " "
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return {
            "posts": chunks[:20],
            "links": self._extract_links_from_html(response.text),
            "platform": "unknown"
        }
    
    def _detect_platform(self, identifier: str) -> str:
        """Detect the platform from an identifier."""
        lower_id = identifier.lower()
        
        if 'twitter.com' in lower_id or 'x.com' in lower_id:
            return "twitter"
        elif 'facebook.com' in lower_id:
            return "facebook"
        elif 'reddit.com' in lower_id:
            return "reddit"
        elif 'youtube.com' in lower_id:
            return "youtube"
        elif '.bsky.app' in lower_id or 'bsky.app' in lower_id:
            return "bsky"
        elif 'medium.com' in lower_id:
            return "medium"
        elif any(domain in lower_id for domain in ['mastodon.social', 'mastodon.online', 'masto.ai']):
            return "mastodon"
        else:
            return "unknown"
    
    def fetch_profile_data(self, identifier: str, platform: str = None) -> Dict[str, Any]:
        """
        Fetch data from a profile on a given platform.
        
        Args:
            identifier: The profile identifier
            platform: The platform name (optional, will be detected if not provided)
        
        Returns:
            Dictionary with profile data including posts and links
        """
        # Detect platform if not provided
        if not platform or platform == "unknown":
            platform = self._detect_platform(identifier)
        
        # Get the appropriate fetcher
        fetcher = self.platform_fetchers.get(platform, self._fetch_generic_data)
        
        # Fetch data
        return fetcher(identifier)
