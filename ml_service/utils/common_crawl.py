#!/usr/bin/env python3
"""
Common Crawl Analyzer for Shinigami Eyes ML service.
Analyzes websites using Common Crawl data for semantic web analysis.
"""

import os
import logging
import json
import re
import time
import requests
import tempfile
import gzip
from typing import List, Dict, Any, Optional, Set
from urllib.parse import urlparse
import warcio
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class CommonCrawlAnalyzer:
    """Analyzes websites using Common Crawl data."""
    
    def __init__(self):
        """Initialize the Common Crawl analyzer."""
        # Cache directory for downloaded WARC files
        self.cache_dir = os.path.join(tempfile.gettempdir(), "shinigami_cc_cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Cache expiry (7 days)
        self.cache_expiry = 7 * 24 * 60 * 60
        
        # Latest available Common Crawl index
        self.cc_index = self._get_latest_cc_index()
        
        # Websites known to be typically transphobic
        self.known_transphobic_domains = {
            'kiwifarms.net',
            'ovarit.com',
            'rodeoh.com',
            'familyresearchcouncil.org',
            'heritage.org',
            'breitbart.com',
            'dailywire.com',
            'thefederalist.com',
            'lifesitenews.com',
            'womenspaceinternational.org',
            'womenarexx.org',
            'standingforsex.org',
            'womenarehuman.com',
            'fairplayforwomen.com',
            'womensdeclaration.com',
            'detransvoices.org',
            'terfisaslur.com',
            'genspect.org',
            'transgender-trend.com',
            'pitt.substack.com',
            'jessesingal.substack.com',
            'grahamlinehan.substack.com',
            'fencesitterz.substack.com',
            'abigailshrier.substack.com',
            'pduffy.substack.com',
            'michaelshellenberger.substack.com',
            'thepostmillennial.com',
            'fpiw.org',
        }
        
        # Websites known to be typically trans-friendly
        self.known_transfriendly_domains = {
            'glaad.org',
            'transequality.org',
            'thetrevorproject.org',
            'glsen.org',
            'pflag.org',
            'mermaidsuk.org.uk',
            'tgeu.org',
            'transhub.org.au',
            'genderspectrum.org',
            'transathlete.com',
            'transpulseproject.ca',
            'translawcenter.org',
            'transmascnetwork.org',
            'translifeline.org',
            'itgetsbetter.org',
            'gender.wikia.org',
            'transadvocate.com',
            'transjournalists.org',
            'juliaserano.com',
            'transstudent.org',
            'transyouthequality.org',
            'point5cc.com',
            'genderanalysis.net',
            'translash.org',
            'autostraddle.com',
            'them.us',
            'bitchmedia.org',
            'everydayfeminism.com',
        }
        
        # Cache for link analysis results
        self.link_analysis_cache = {}
    
    def status(self) -> Dict[str, Any]:
        """Return the status of the analyzer."""
        return {
            "cc_index": self.cc_index,
            "cache_dir": self.cache_dir,
            "known_transphobic_domains": len(self.known_transphobic_domains),
            "known_transfriendly_domains": len(self.known_transfriendly_domains)
        }
    
    def _get_latest_cc_index(self) -> str:
        """Get the latest available Common Crawl index."""
        try:
            response = requests.get("https://index.commoncrawl.org/collinfo.json")
            if response.status_code == 200:
                indices = response.json()
                # Get the most recent index
                if indices and len(indices) > 0:
                    return indices[0]['id']
            
            # Fallback to a known index
            return "CC-MAIN-2023-14"
            
        except Exception as e:
            logger.error(f"Failed to get latest Common Crawl index: {str(e)}")
            return "CC-MAIN-2023-14"  # Fallback to a known index
    
    def _get_domain_from_url(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            parsed = urlparse(url if url.startswith('http') else f"https://{url}")
            domain = parsed.netloc.lower()
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except:
            return url.lower()
    
    def _check_known_domain_stance(self, domain: str) -> Optional[Dict[str, Any]]:
        """Check if domain is in known lists."""
        if domain in self.known_transphobic_domains:
            return {
                "classification": 2,  # Transphobic
                "confidence": 0.85,
                "source": "known_transphobic_domain"
            }
        elif domain in self.known_transfriendly_domains:
            return {
                "classification": 0,  # Trans-friendly
                "confidence": 0.85,
                "source": "known_transfriendly_domain"
            }
        return None
    
    def _fetch_cc_records_for_domain(self, domain: str) -> List[Dict[str, Any]]:
        """Fetch Common Crawl records for a domain."""
        try:
            # Query the Common Crawl index
            query_url = f"https://index.commoncrawl.org/{self.cc_index}-index?url=*.{domain}/*&output=json"
            response = requests.get(query_url)
            
            if response.status_code != 200:
                logger.warning(f"Common Crawl query failed for {domain}: {response.status_code}")
                return []
            
            # Parse the response (JSON lines format)
            results = []
            for line in response.text.strip().split('\n'):
                if line:
                    try:
                        record = json.loads(line)
                        results.append(record)
                    except:
                        pass
            
            return results[:10]  # Limit to 10 records for efficiency
            
        except Exception as e:
            logger.error(f"Failed to fetch Common Crawl records for {domain}: {str(e)}")
            return []
    
    def _fetch_warc_record(self, record: Dict[str, Any]) -> Optional[str]:
        """Fetch WARC record content."""
        try:
            filename = record.get('filename')
            offset = int(record.get('offset', 0))
            length = int(record.get('length', 0))
            
            if not filename or offset < 0 or length <= 0:
                return None
            
            # Construct URL for range request
            url = f"https://data.commoncrawl.org/{filename}"
            headers = {'Range': f'bytes={offset}-{offset+length-1}'}
            
            response = requests.get(url, headers=headers)
            if response.status_code != 206:  # Partial Content
                return None
            
            # Parse WARC record
            content = None
            try:
                with warcio.archiveiterator.ArchiveIterator(
                    warcio.bufferedreaders.BufferedReader(response.content)
                ) as archive_iterator:
                    for record in archive_iterator:
                        if record.rec_type == 'response':
                            content = record.content_stream().read().decode('utf-8', errors='ignore')
                            break
            except:
                pass
            
            return content
            
        except Exception as e:
            logger.error(f"Failed to fetch WARC record: {str(e)}")
            return None
    
    def _extract_text_from_html(self, html: str) -> str:
        """Extract text content from HTML."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove script and style elements
            for script in soup(['script', 'style']):
                script.extract()
            
            # Get text
            text = soup.get_text()
            
            # Break into lines and remove leading and trailing space
            lines = (line.strip() for line in text.splitlines())
            # Break multi-headlines into a line each
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            # Drop blank lines
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return text
            
        except Exception as e:
            logger.error(f"Failed to extract text from HTML: {str(e)}")
            return ""
    
    def _analyze_domain_content(self, domain: str) -> Dict[str, Any]:
        """Analyze content from a domain using Common Crawl data."""
        # Check if domain is already in known lists
        known_stance = self._check_known_domain_stance(domain)
        if known_stance:
            return known_stance
        
        # Fetch Common Crawl records
        records = self._fetch_cc_records_for_domain(domain)
        if not records:
            return {
                "classification": 1,  # Gray area due to lack of data
                "confidence": 0.1,
                "source": "no_cc_data"
            }
        
        # Collect text content from records
        contents = []
        for record in records[:3]:  # Limit to 3 to avoid overloading
            content = self._fetch_warc_record(record)
            if content:
                text = self._extract_text_from_html(content)
                if text:
                    contents.append(text[:10000])  # Limit size
        
        if not contents:
            return {
                "classification": 1,  # Gray area due to lack of data
                "confidence": 0.1,
                "source": "no_content_extracted"
            }
        
        # Basic content analysis (simplified version)
        # In a real implementation, you would use the ContentAnalyzer here
        
        # Look for transphobic patterns
        transphobic_patterns = [
            r'\b(only\s+two\s+genders|attack\s+helicopter|basic\s+biology|genital\s+mutilation)\b',
            r'\b(trans\s*cult|trans\s*ideology|tr[a@]nn[y!ie]|alphabet\s+mafia|lgb\s*drop\s*the\s*t)\b',
            r'\b(gender\s*confused|gender\s*delusion|transgenderism|gender\s*ideology|woke\s*gender)\b'
        ]
        
        # Look for trans-friendly patterns
        friendly_patterns = [
            r'\b(trans\s*rights|trans\s*women\s*are\s*women|trans\s*men\s*are\s*men|protect\s*trans\s*kids)\b',
            r'\b(gender\s*affirming|respect\s*pronouns|transgender\s*visibility|support\s*trans)\b',
            r'\b(gender\s*expression|gender\s*identity|nonbinary\s*rights|trans\s*healthcare|gender\s*euphoria)\b'
        ]
        
        # Count matches
        transphobic_count = 0
        friendly_count = 0
        
        for content in contents:
            content_lower = content.lower()
            for pattern in transphobic_patterns:
                transphobic_count += len(re.findall(pattern, content_lower))
            for pattern in friendly_patterns:
                friendly_count += len(re.findall(pattern, content_lower))
        
        # Determine classification
        total_matches = transphobic_count + friendly_count
        if total_matches == 0:
            return {
                "classification": 1,  # Gray area
                "confidence": 0.3,
                "source": "pattern_analysis",
                "matches": {
                    "transphobic": 0,
                    "friendly": 0
                }
            }
        
        transphobic_ratio = transphobic_count / total_matches
        
        if transphobic_ratio > 0.7:
            classification = 2  # Transphobic
            confidence = 0.5 + min(0.4, transphobic_ratio - 0.7)
        elif transphobic_ratio < 0.3:
            classification = 0  # Trans-friendly
            confidence = 0.5 + min(0.4, 0.3 - transphobic_ratio)
        else:
            classification = 1  # Gray area
            confidence = 0.3
        
        return {
            "classification": classification,
            "confidence": confidence,
            "source": "pattern_analysis",
            "matches": {
                "transphobic": transphobic_count,
                "friendly": friendly_count
            }
        }
    
    def analyze_single_url(self, url: str) -> Dict[str, Any]:
        """
        Analyze a single URL using Common Crawl data.
        
        Args:
            url: The URL to analyze
            
        Returns:
            Analysis results
        """
        domain = self._get_domain_from_url(url)
        
        # Check cache
        cache_key = f"domain:{domain}"
        if cache_key in self.link_analysis_cache:
            return self.link_analysis_cache[cache_key]
        
        result = self._analyze_domain_content(domain)
        
        # Cache result
        self.link_analysis_cache[cache_key] = result
        
        return result
    
    def analyze_links(self, links: List[str]) -> Dict[str, Any]:
        """
        Analyze multiple links to determine overall classification.
        
        Args:
            links: List of URLs to analyze
            
        Returns:
            Aggregated analysis results
        """
        if not links:
            return {
                "classification": 1,  # Gray area
                "confidence": 0.1,
                "error": "no_links"
            }
        
        # Get unique domains
        domains = set()
        for link in links:
            domain = self._get_domain_from_url(link)
            if domain:
                domains.add(domain)
        
        if not domains:
            return {
                "classification": 1,  # Gray area
                "confidence": 0.1,
                "error": "no_valid_domains"
            }
        
        # Analyze each domain
        results = []
        for domain in domains:
            known_stance = self._check_known_domain_stance(domain)
            if known_stance:
                results.append({
                    "domain": domain,
                    "result": known_stance
                })
                continue
            
            # Skip detailed analysis for unknown domains if we already have enough results
            if len(results) >= 5:
                continue
            
            # Cache key
            cache_key = f"domain:{domain}"
            
            # Check cache
            if cache_key in self.link_analysis_cache:
                results.append({
                    "domain": domain,
                    "result": self.link_analysis_cache[cache_key]
                })
                continue
            
            # Analyze domain
            result = self._analyze_domain_content(domain)
            
            # Cache result
            self.link_analysis_cache[cache_key] = result
            
            results.append({
                "domain": domain,
                "result": result
            })
        
        # Calculate weighted average classification
        if not results:
            return {
                "classification": 1,  # Gray area
                "confidence": 0.1,
                "error": "no_analysis_results"
            }
        
        classifications = []
        confidences = []
        
        for result in results:
            domain_result = result["result"]
            classifications.append(domain_result["classification"])
            confidences.append(domain_result["confidence"])
        
        # Calculate weighted average
        weighted_sum = sum(c * conf for c, conf in zip(classifications, confidences))
        total_confidence = sum(confidences)
        
        if total_confidence > 0:
            weighted_avg = weighted_sum / total_confidence
        else:
            weighted_avg = 1  # Default to gray area
        
        # Determine final classification
        if weighted_avg > 1.6:
            final_classification = 2  # Transphobic
        elif weighted_avg < 0.4:
            final_classification = 0  # Trans-friendly
        else:
            final_classification = 1  # Gray area
        
        # Calculate overall confidence
        overall_confidence = sum(confidences) / len(confidences)
        
        return {
            "classification": final_classification,
            "confidence": overall_confidence,
            "weighted_avg": weighted_avg,
            "domains_analyzed": len(results),
            "domain_results": [
                {
                    "domain": r["domain"],
                    "classification": r["result"]["classification"],
                    "confidence": r["result"]["confidence"]
                } for r in results
            ]
        }
