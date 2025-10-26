"""
ML Classification Service
Handles content classification using transformer models
"""
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import torch
import re
import logging
from typing import Dict, Any
import asyncio
from functools import lru_cache

logger = logging.getLogger(__name__)


class ContentClassifier:
    """
    Multi-purpose content classifier using pre-trained transformer models
    
    Classifies content into:
    - Toxicity: toxic, severe_toxic, obscene, threat, insult
    - Spam: promotional, repetitive patterns
    - Sentiment: positive, negative, neutral
    
    Final classification: acceptable, needs_review, toxic, spam
    """
    
    def __init__(self):
        """Initialize ML models"""
        self.model_version = "1.0.0"
        self.device = 0 if torch.cuda.is_available() else -1
        
        logger.info(f"Initializing ML models on device: {'GPU' if self.device == 0 else 'CPU'}")
        
        # Load toxicity detection model
        try:
            self.toxicity_classifier = pipeline(
                "text-classification",
                model="unitary/toxic-bert",
                device=self.device,
                max_length=512,
                truncation=True
            )
            logger.info("Toxicity classifier loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load toxic-bert, using fallback: {e}")
            self.toxicity_classifier = pipeline(
                "sentiment-analysis",
                model="distilbert-base-uncased-finetuned-sst-2-english",
                device=self.device
            )
        
        # Load sentiment analysis model
        self.sentiment_classifier = pipeline(
            "sentiment-analysis",
            model="distilbert-base-uncased-finetuned-sst-2-english",
            device=self.device
        )
        logger.info("Sentiment classifier loaded successfully")
        
        # Spam detection patterns
        self.spam_patterns = [
            r'(?i)click here',
            r'(?i)buy now',
            r'(?i)limited time',
            r'(?i)act now',
            r'(?i)free money',
            r'(?i)winner',
            r'(?i)congratulations.*won',
            r'https?://[^\s]+.*https?://[^\s]+.*https?://[^\s]+',  # Multiple URLs
            r'(.)\1{4,}',  # Repeated characters
        ]
        
        # Classification thresholds
        self.thresholds = {
            'toxicity_high': 0.8,
            'toxicity_medium': 0.6,
            'spam_high': 0.7,
            'confidence_low': 0.6
        }
        
        logger.info("ContentClassifier initialized successfully")
    
    async def classify(self, content: str) -> Dict[str, Any]:
        """
        Classify content and return comprehensive results
        
        Args:
            content: Text content to classify
            
        Returns:
            Dict containing classification, scores, and metadata
        """
        # Run classification in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._classify_sync, content)
        return result
    
    def _classify_sync(self, content: str) -> Dict[str, Any]:
        """Synchronous classification logic"""
        try:
            # 1. Toxicity Detection
            toxicity_result = self._detect_toxicity(content)
            toxicity_score = toxicity_result['score']
            
            # 2. Spam Detection
            spam_score = self._detect_spam(content)
            
            # 3. Sentiment Analysis
            sentiment_result = self._analyze_sentiment(content)
            
            # 4. Determine final classification
            classification, confidence = self._determine_classification(
                toxicity_score,
                spam_score,
                sentiment_result
            )
            
            result = {
                'classification': classification,
                'confidence': confidence,
                'toxicity_score': toxicity_score,
                'spam_score': spam_score,
                'sentiment': sentiment_result['label'],
                'sentiment_score': sentiment_result['score'],
                'threshold': self.thresholds.get(f'{classification}_high', 0.5),
                'model_version': self.model_version,
                'content_length': len(content),
                'word_count': len(content.split())
            }
            
            logger.debug(f"Classification result: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Classification error: {e}", exc_info=True)
            # Return safe default on error
            return {
                'classification': 'needs_review',
                'confidence': 0.0,
                'toxicity_score': 0.0,
                'spam_score': 0.0,
                'sentiment': 'neutral',
                'sentiment_score': 0.5,
                'threshold': 0.0,
                'model_version': self.model_version,
                'error': str(e)
            }
    
    def _detect_toxicity(self, content: str) -> Dict[str, Any]:
        """Detect toxic content using transformer model"""
        try:
            # Get toxicity prediction
            result = self.toxicity_classifier(content[:512])[0]
            
            # Normalize score based on label
            if result['label'].lower() in ['toxic', 'negative']:
                score = result['score']
            else:
                score = 1.0 - result['score']
            
            return {
                'label': result['label'],
                'score': min(max(score, 0.0), 1.0)  # Clamp to [0, 1]
            }
        except Exception as e:
            logger.error(f"Toxicity detection error: {e}")
            return {'label': 'unknown', 'score': 0.0}
    
    def _detect_spam(self, content: str) -> float:
        """
        Detect spam content using pattern matching and heuristics
        
        Returns:
            Spam score between 0.0 and 1.0
        """
        score = 0.0
        
        # Check spam patterns
        pattern_matches = 0
        for pattern in self.spam_patterns:
            if re.search(pattern, content):
                pattern_matches += 1
        
        # Calculate pattern score (0-0.5)
        if pattern_matches > 0:
            score += min(pattern_matches * 0.15, 0.5)
        
        # Check for excessive capitalization
        if len(content) > 10:
            caps_ratio = sum(1 for c in content if c.isupper()) / len(content)
            if caps_ratio > 0.5:
                score += 0.2
        
        # Check for excessive punctuation
        punct_count = sum(1 for c in content if c in '!?.')
        if punct_count > 5:
            score += 0.15
        
        # Check for very short repetitive content
        words = content.split()
        if len(words) > 3:
            unique_ratio = len(set(words)) / len(words)
            if unique_ratio < 0.3:
                score += 0.2
        
        return min(score, 1.0)
    
    def _analyze_sentiment(self, content: str) -> Dict[str, Any]:
        """Analyze sentiment of content"""
        try:
            result = self.sentiment_classifier(content[:512])[0]
            return {
                'label': result['label'].lower(),
                'score': result['score']
            }
        except Exception as e:
            logger.error(f"Sentiment analysis error: {e}")
            return {'label': 'neutral', 'score': 0.5}
    
    def _determine_classification(
        self,
        toxicity_score: float,
        spam_score: float,
        sentiment_result: Dict[str, Any]
    ) -> tuple[str, float]:
        """
        Determine final classification based on all scores
        
        Classification rules:
        1. High toxicity (>0.8) -> toxic
        2. High spam (>0.7) -> spam
        3. Medium toxicity (0.6-0.8) OR medium spam (0.5-0.7) -> needs_review
        4. Low confidence in any metric -> needs_review
        5. Otherwise -> acceptable
        
        Returns:
            Tuple of (classification, confidence)
        """
        # Calculate overall confidence
        confidence = 1.0 - max(
            abs(toxicity_score - 0.5) if toxicity_score < 0.6 else 0,
            abs(spam_score - 0.5) if spam_score < 0.6 else 0
        )
        
        # Classification logic
        if toxicity_score >= self.thresholds['toxicity_high']:
            return ('toxic', toxicity_score)
        
        if spam_score >= self.thresholds['spam_high']:
            return ('spam', spam_score)
        
        if toxicity_score >= self.thresholds['toxicity_medium']:
            return ('needs_review', max(toxicity_score, 0.6))
        
        if spam_score >= 0.5:
            return ('needs_review', max(spam_score, 0.6))
        
        # Check if confidence is too low
        if confidence < self.thresholds['confidence_low']:
            return ('needs_review', confidence)
        
        # Content appears acceptable
        return ('acceptable', confidence)
    
    def update_thresholds(self, new_thresholds: Dict[str, float]):
        """Update classification thresholds for tuning"""
        self.thresholds.update(new_thresholds)
        logger.info(f"Thresholds updated: {self.thresholds}")
    
    @lru_cache(maxsize=1000)
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about loaded models"""
        return {
            'version': self.model_version,
            'toxicity_model': 'unitary/toxic-bert',
            'sentiment_model': 'distilbert-base-uncased-finetuned-sst-2-english',
            'device': 'GPU' if self.device == 0 else 'CPU',
            'thresholds': self.thresholds
        }


# Standalone test function
if __name__ == "__main__":
    import asyncio
    
    async def test_classifier():
        """Test the classifier with sample inputs"""
        classifier = ContentClassifier()
        
        test_cases = [
            "This is a great product! I love it!",
            "You are stupid and worthless, go away!",
            "Click here NOW! Limited time offer! Buy now! Free money!!!",
            "What's the weather like today?",
            "I disagree with your opinion, but I respect your viewpoint."
        ]
        
        print("\n" + "="*60)
        print("TESTING CONTENT CLASSIFIER")
        print("="*60 + "\n")
        
        for i, content in enumerate(test_cases, 1):
            print(f"Test Case {i}: {content[:50]}...")
            result = await classifier.classify(content)
            print(f"Classification: {result['classification']}")
            print(f"Confidence: {result['confidence']:.3f}")
            print(f"Toxicity: {result['toxicity_score']:.3f}")
            print(f"Spam: {result['spam_score']:.3f}")
            print(f"Sentiment: {result['sentiment']}")
            print("-" * 60 + "\n")
    
    asyncio.run(test_classifier())