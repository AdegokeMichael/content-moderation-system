"""
Comprehensive Test Suite for Content Moderation System
Tests API endpoints, classification logic, and database operations
"""
import pytest
import asyncio
import httpx
import json
from datetime import datetime
from typing import Dict, Any

# Test configuration
API_BASE_URL = "http://localhost:8000"
TEST_TIMEOUT = 30


class TestContentModerationAPI:
    """Test suite for Content Moderation API"""
    
    @pytest.fixture
    async def client(self):
        """Create async HTTP client"""
        async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=TEST_TIMEOUT) as client:
            yield client
    
    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health check endpoint"""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "database" in data
        print("✓ Health check passed")
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "operational"
        assert "version" in data
        print("✓ Root endpoint passed")
    
    @pytest.mark.asyncio
    async def test_acceptable_content(self, client):
        """Test acceptable content classification"""
        payload = {
            "content": "This is a great product! I really enjoy using it.",
            "author_id": "test_user_001",
            "platform": "web",
            "metadata": {"source": "test"}
        }
        
        response = await client.post("/api/v1/content/submit", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["classification"] == "acceptable"
        assert data["confidence"] > 0.5
        assert data["action_taken"] == "approved_and_stored"
        assert "content_id" in data
        
        print(f"✓ Acceptable content test passed")
        print(f"  - Classification: {data['classification']}")
        print(f"  - Confidence: {data['confidence']:.3f}")
        print(f"  - Content ID: {data['content_id']}")
    
    @pytest.mark.asyncio
    async def test_toxic_content(self, client):
        """Test toxic content detection"""
        payload = {
            "content": "You are stupid and worthless! I hate you!",
            "author_id": "test_user_002",
            "platform": "mobile"
        }
        
        response = await client.post("/api/v1/content/submit", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["classification"] in ["toxic", "needs_review"]
        assert data["toxicity_score"] > 0.4
        assert data["action_taken"] in ["rejected_toxic", "queued_for_review"]
        
        print(f"✓ Toxic content test passed")
        print(f"  - Classification: {data['classification']}")
        print(f"  - Toxicity Score: {data['toxicity_score']:.3f}")
        print(f"  - Action: {data['action_taken']}")
    
    @pytest.mark.asyncio
    async def test_spam_content(self, client):
        """Test spam detection"""
        payload = {
            "content": "Click here NOW!!! Buy now! Limited time offer! Act fast! Free money! Winner!",
            "author_id": "test_user_003",
            "platform": "web"
        }
        
        response = await client.post("/api/v1/content/submit", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["classification"] in ["spam", "needs_review"]
        assert data["spam_score"] > 0.4
        assert data["action_taken"] in ["rejected_spam", "queued_for_review"]
        
        print(f"✓ Spam content test passed")
        print(f"  - Classification: {data['classification']}")
        print(f"  - Spam Score: {data['spam_score']:.3f}")
        print(f"  - Action: {data['action_taken']}")
    
    @pytest.mark.asyncio
    async def test_ambiguous_content(self, client):
        """Test content that needs human review"""
        payload = {
            "content": "I'm not entirely sure about this new policy.",
            "author_id": "test_user_004",
            "platform": "web"
        }
        
        response = await client.post("/api/v1/content/submit", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        # Could be acceptable or needs review depending on thresholds
        assert data["classification"] in ["acceptable", "needs_review"]
        
        print(f"✓ Ambiguous content test passed")
        print(f"  - Classification: {data['classification']}")
        print(f"  - Confidence: {data['confidence']:.3f}")
    
    @pytest.mark.asyncio
    async def test_invalid_content_empty(self, client):
        """Test validation for empty content"""
        payload = {
            "content": "",
            "author_id": "test_user_005",
            "platform": "web"
        }
        
        response = await client.post("/api/v1/content/submit", json=payload)
        assert response.status_code == 422  # Validation error
        
        print("✓ Empty content validation passed")
    
    @pytest.mark.asyncio
    async def test_invalid_author_id(self, client):
        """Test validation for missing author ID"""
        payload = {
            "content": "Test content",
            "author_id": "",
            "platform": "web"
        }
        
        response = await client.post("/api/v1/content/submit", json=payload)
        assert response.status_code == 422
        
        print("✓ Invalid author ID validation passed")
    
    @pytest.mark.asyncio
    async def test_long_content(self, client):
        """Test handling of long content"""
        payload = {
            "content": "This is a test. " * 200,  # ~3000 characters
            "author_id": "test_user_006",
            "platform": "web"
        }
        
        response = await client.post("/api/v1/content/submit", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "classification" in data
        
        print(f"✓ Long content test passed")
        print(f"  - Content length: {len(payload['content'])} chars")
        print(f"  - Classification: {data['classification']}")
    
    @pytest.mark.asyncio
    async def test_statistics_endpoint(self, client):
        """Test statistics endpoint"""
        response = await client.get("/api/v1/stats/overview")
        assert response.status_code == 200
        
        data = response.json()
        assert "total_content" in data
        assert isinstance(data["total_content"], int)
        
        print("✓ Statistics endpoint passed")
        print(f"  - Total content: {data.get('total_content', 0)}")
        print(f"  - Acceptable: {data.get('acceptable', 0)}")
        print(f"  - Needs review: {data.get('needs_review', 0)}")
        print(f"  - Toxic: {data.get('toxic', 0)}")
        print(f"  - Spam: {data.get('spam', 0)}")
    
    @pytest.mark.asyncio
    async def test_model_drift_endpoint(self, client):
        """Test model drift metrics endpoint"""
        response = await client.get("/api/v1/stats/model-drift")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        
        print("✓ Model drift endpoint passed")
        print(f"  - Metric records: {len(data)}")
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, client):
        """Test handling of concurrent requests"""
        payloads = [
            {
                "content": f"Test content number {i}",
                "author_id": f"concurrent_user_{i}",
                "platform": "web"
            }
            for i in range(5)
        ]
        
        tasks = [
            client.post("/api/v1/content/submit", json=payload)
            for payload in payloads
        ]
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful = sum(1 for r in responses if not isinstance(r, Exception) and r.status_code == 200)
        assert successful >= 4  # At least 80% success rate
        
        print(f"✓ Concurrent requests test passed")
        print(f"  - Successful: {successful}/5")
    
    @pytest.mark.asyncio
    async def test_metadata_handling(self, client):
        """Test metadata field handling"""
        payload = {
            "content": "Test with metadata",
            "author_id": "test_user_007",
            "platform": "web",
            "metadata": {
                "ip_address": "192.168.1.1",
                "user_agent": "TestBot/1.0",
                "session_id": "abc123"
            }
        }
        
        response = await client.post("/api/v1/content/submit", json=payload)
        assert response.status_code == 200
        
        print("✓ Metadata handling test passed")
    
    @pytest.mark.asyncio
    async def test_special_characters(self, client):
        """Test handling of special characters and unicode"""
        payload = {
            "content": "Test with émojis 🎉🚀 and spëcial çharacters!",
            "author_id": "test_user_008",
            "platform": "web"
        }
        
        response = await client.post("/api/v1/content/submit", json=payload)
        assert response.status_code == 200
        
        print("✓ Special characters test passed")


class TestClassificationLogic:
    """Test classification business logic"""
    
    test_cases = [
        {
            "name": "Positive review",
            "content": "Excellent service! Highly recommended.",
            "expected_classification": "acceptable",
            "min_confidence": 0.6
        },
        {
            "name": "Constructive criticism",
            "content": "The product is good but could use some improvements.",
            "expected_classification": "acceptable",
            "min_confidence": 0.5
        },
        {
            "name": "Severe toxicity",
            "content": "I will kill you! You deserve to die!",
            "expected_classification": "toxic",
            "min_toxicity": 0.6
        },
        {
            "name": "Promotional spam",
            "content": "CLICK HERE NOW!!! FREE GIFT! LIMITED TIME! BUY NOW!!!",
            "expected_classification": "spam",
            "min_spam": 0.5
        },
        {
            "name": "Neutral inquiry",
            "content": "What are the operating hours?",
            "expected_classification": "acceptable",
            "min_confidence": 0.5
        }
    ]
    
    @pytest.mark.asyncio
    async def test_classification_accuracy(self):
        """Test classification accuracy across multiple test cases"""
        async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=TEST_TIMEOUT) as client:
            results = []
            
            print("\n" + "="*70)
            print("CLASSIFICATION ACCURACY TEST")
            print("="*70)
            
            for i, test_case in enumerate(self.test_cases, 1):
                payload = {
                    "content": test_case["content"],
                    "author_id": f"test_accuracy_{i}",
                    "platform": "test"
                }
                
                response = await client.post("/api/v1/content/submit", json=payload)
                assert response.status_code == 200
                
                data = response.json()
                
                # Check classification
                passed = True
                if "expected_classification" in test_case:
                    # Allow acceptable or needs_review for ambiguous cases
                    if test_case["expected_classification"] == "acceptable":
                        passed = data["classification"] in ["acceptable", "needs_review"]
                    else:
                        passed = data["classification"] == test_case["expected_classification"] or \
                                data["classification"] == "needs_review"
                
                # Check minimum scores
                if "min_confidence" in test_case:
                    passed = passed and data["confidence"] >= test_case["min_confidence"]
                if "min_toxicity" in test_case:
                    passed = passed and data["toxicity_score"] >= test_case["min_toxicity"]
                if "min_spam" in test_case:
                    passed = passed and data["spam_score"] >= test_case["min_spam"]
                
                results.append(passed)
                
                status = "✓" if passed else "✗"
                print(f"\n{status} Test {i}: {test_case['name']}")
                print(f"  Content: {test_case['content'][:50]}...")
                print(f"  Expected: {test_case.get('expected_classification', 'N/A')}")
                print(f"  Actual: {data['classification']}")
                print(f"  Confidence: {data['confidence']:.3f}")
                print(f"  Toxicity: {data['toxicity_score']:.3f}")
                print(f"  Spam: {data['spam_score']:.3f}")
            
            accuracy = sum(results) / len(results)
            print(f"\n{'='*70}")
            print(f"Overall Accuracy: {accuracy*100:.1f}% ({sum(results)}/{len(results)})")
            print(f"{'='*70}\n")
            
            # Require at least 60% accuracy
            assert accuracy >= 0.6, f"Classification accuracy too low: {accuracy*100:.1f}%"


# Run tests
if __name__ == "__main__":
    print("\n" + "="*70)
    print("CONTENT MODERATION SYSTEM - AUTOMATED TEST SUITE")
    print("="*70 + "\n")
    
    # Run pytest with verbose output
    pytest.main([
        __file__,
        "-v",
        "--asyncio-mode=auto",
        "--tb=short",
        "-s"  # Show print statements
    ])