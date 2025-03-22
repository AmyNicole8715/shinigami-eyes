#!/usr/bin/env python3
"""
Content Analyzer for Shinigami Eyes ML service.
Uses Ollama with Gemma 3:4b to analyze text content.
"""

import os
import logging
import json
import requests
import re
import spacy
import numpy as np
from typing import List, Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)

class ContentAnalyzer:
    """Analyzes text content to determine if it's transphobic or trans-friendly."""
    
    def __init__(self, model_name: str = "transphobia-detector"):
        """
        Initialize the content analyzer.
        
        Args:
            model_name: Name of the Ollama model to use. Defaults to "transphobia-detector".
        """
        self.model_name = model_name
        self.ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
        
        # Load spaCy for text preprocessing
        try:
            self.nlp = spacy.load("en_core_web_md")
            logger.info("Loaded spaCy model for text preprocessing")
        except:
            logger.warning("Could not load spaCy model - running without preprocessing")
            self.nlp = None
        
        # Check if Ollama is available
        self.ollama_available = self._check_ollama()
        
        # Use spaCy as fallback if Ollama isn't available
        if not self.ollama_available:
            logger.warning("Ollama not available. Using spaCy for basic analysis instead.")
            
        # Classification labels
        self.labels = {
            0: "t-friendly",
            1: "gray-area",
            2: "transphobic"
        }
        
        # Common transphobic terms and patterns (for fallback analysis)
        self.transphobic_patterns = [
            r'\b(only\s+two\s+genders|attack\s+helicopter|basic\s+biology|genital\s+mutilation)\b',
            r'\b(trans\s*cult|trans\s*ideology|tr[a@]nn[y!ie]|alphabet\s+mafia|lgb\s*drop\s*the\s*t)\b',
            r'\b(gender\s*confused|gender\s*delusion|transgenderism|gender\s*ideology|woke\s*gender)\b'
        ]
        
        # Common trans-friendly terms and patterns (for fallback analysis)
        self.friendly_patterns = [
            r'\b(trans\s*rights|trans\s*women\s*are\s*women|trans\s*men\s*are\s*men|protect\s*trans\s*kids)\b',
            r'\b(gender\s*affirming|respect\s*pronouns|transgender\s*visibility|support\s*trans)\b',
            r'\b(gender\s*expression|gender\s*identity|nonbinary\s*rights|trans\s*healthcare|gender\s*euphoria)\b'
        ]
        
    def _check_ollama(self) -> bool:
        """Check if Ollama is available and has our model."""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                return any(model.get("name") == self.model_name for model in models)
            return False
        except:
            return False
    
    def status(self) -> Dict[str, Any]:
        """Return the status of the analyzer."""
        return {
            "ollama_available": self.ollama_available,
            "model_name": self.model_name,
            "spacy_available": self.nlp is not None
        }
    
    def preprocess_text(self, text: str) -> str:
        """Preprocess text for analysis."""
        if not text:
            return ""
            
        # Basic cleaning
        text = re.sub(r'https?://\S+', '', text)  # Remove URLs
        text = re.sub(r'[^\w\s.,!?]', ' ', text)  # Remove special characters
        text = re.sub(r'\s+', ' ', text).strip()  # Normalize whitespace
        
        if self.nlp:
            doc = self.nlp(text[:100000])  # Limit size for memory reasons
            # Remove stopwords and get lemmas
            tokens = [token.lemma_ for token in doc if not token.is_stop and not token.is_punct]
            return " ".join(tokens)
        
        return text
    
    def analyze_with_ollama(self, text: str) -> Dict[str, Any]:
        """Analyze text using Ollama model."""
        prompt = f"Analyze this content and determine if it's transphobic or trans-friendly. Respond with only the number:\n0 = trans-friendly\n1 = unclear or needs more context\n2 = transphobic\n\nContent: {text}"
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                # Extract just the numeric classification from response
                classification_text = result.get("response", "1").strip()
                classification_match = re.search(r'[0-2]', classification_text)
                
                if classification_match:
                    classification = int(classification_match.group(0))
                else:
                    # Default to gray area if no clear classification
                    classification = 1
                    
                return {
                    "classification": classification,
                    "label": self.labels[classification],
                    "confidence": 0.8,  # Ollama doesn't provide confidence scores
                    "method": "ollama"
                }
                
            else:
                logger.error(f"Ollama API error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error calling Ollama: {str(e)}")
            return None
    
    def analyze_with_patterns(self, text: str) -> Dict[str, Any]:
        """Fallback analysis using regex patterns."""
        text = text.lower()
        
        # Count matches for transphobic and friendly patterns
        transphobic_count = sum(len(re.findall(pattern, text)) for pattern in self.transphobic_patterns)
        friendly_count = sum(len(re.findall(pattern, text)) for pattern in self.friendly_patterns)
        
        # Calculate scores
        total_matches = transphobic_count + friendly_count
        if total_matches == 0:
            return {
                "classification": 1,  # Gray area due to no matches
                "label": self.labels[1],
                "confidence": 0.3,
                "method": "pattern_matching"
            }
        
        transphobic_score = transphobic_count / total_matches if total_matches > 0 else 0
        
        # Determine classification
        if transphobic_score > 0.7:
            classification = 2  # Transphobic
            confidence = 0.5 + (transphobic_score - 0.7) * 1.5  # Scale from 0.5 to 0.95
        elif transphobic_score < 0.3:
            classification = 0  # Trans-friendly
            confidence = 0.5 + (0.3 - transphobic_score) * 1.5  # Scale from 0.5 to 0.95
        else:
            classification = 1  # Gray area
            confidence = 0.3  # Low confidence for gray area
        
        return {
            "classification": classification,
            "label": self.labels[classification],
            "confidence": min(confidence, 0.95),  # Cap at 0.95
            "method": "pattern_matching",
            "pattern_stats": {
                "transphobic_matches": transphobic_count,
                "friendly_matches": friendly_count
            }
        }
    
    def analyze_text(self, text: str) -> Dict[str, Any]:
        """
        Analyze text and determine if it's transphobic or trans-friendly.
        
        Args:
            text: The text to analyze
            
        Returns:
            Dictionary with classification results
        """
        if not text or len(text.strip()) < 5:
            return {
                "classification": 1,  # Gray area
                "label": self.labels[1], 
                "confidence": 0.1,
                "error": "insufficient_text"
            }
        
        # Preprocess text
        processed_text = self.preprocess_text(text)
        
        # First try Ollama
        if self.ollama_available:
            ollama_result = self.analyze_with_ollama(processed_text[:8000])  # Limit size
            if ollama_result:
                return ollama_result
        
        # Fall back to pattern matching
        pattern_result = self.analyze_with_patterns(processed_text)
        return pattern_result
    
    def analyze_profile(self, posts: List[str]) -> Dict[str, Any]:
        """
        Analyze multiple posts from a profile.
        
        Args:
            posts: List of posts or comments from the profile
            
        Returns:
            Aggregated classification results
        """
        if not posts:
            return {
                "classification": 1,  # Gray area
                "label": self.labels[1],
                "confidence": 0.1,
                "error": "no_posts"
            }
        
        # Analyze each post
        results = []
        for post in posts[:20]:  # Limit to 20 posts for efficiency
            result = self.analyze_text(post)
            results.append(result)
        
        # Extract classifications
        classifications = [result["classification"] for result in results]
        confidences = [result["confidence"] for result in results]
        
        # Calculate weighted average
        weighted_classifications = [c * conf for c, conf in zip(classifications, confidences)]
        total_confidence = sum(confidences)
        
        if total_confidence > 0:
            weighted_avg = sum(weighted_classifications) / total_confidence
        else:
            weighted_avg = 1  # Default to gray area
        
        # Determine final classification
        if weighted_avg > 1.6:
            final_classification = 2  # Transphobic
        elif weighted_avg < 0.4:
            final_classification = 0  # Trans-friendly
        else:
            final_classification = 1  # Gray area
        
        # Calculate confidence based on consistency and number of posts
        consistency = 1.0 - (np.std(classifications) / 2.0)  # 0 to 1 scale
        sample_confidence = min(1.0, len(posts) / 10.0)  # 0 to 1 scale
        
        final_confidence = (consistency + sample_confidence) / 2.0
        final_confidence = min(0.95, final_confidence)  # Cap at 0.95
        
        return {
            "classification": final_classification,
            "label": self.labels[final_classification],
            "confidence": final_confidence,
            "sample_size": len(posts),
            "consistency": consistency,
            "method": "profile_analysis",
            "post_distribution": {
                "transphobic": classifications.count(2) / len(classifications),
                "gray_area": classifications.count(1) / len(classifications),
                "friendly": classifications.count(0) / len(classifications)
            }
        }
