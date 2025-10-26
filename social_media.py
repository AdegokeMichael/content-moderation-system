"""
Social Media Integration Module
Handles posting approved content to Facebook and X (Twitter)
"""
import logging
import aiohttp
import asyncio
from typing import Dict, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class SocialMediaPoster:
    """
    Manages posting to multiple social media platforms
    Supports Facebook and X (Twitter)
    """
    
    def __init__(
        self,
        facebook_token: Optional[str] = None,
        twitter_api_key: Optional[str] = None,
        twitter_api_secret: Optional[str] = None,
        twitter_access_token: Optional[str] = None,
        twitter_access_secret: Optional[str] = None
    ):
        """Initialize social media clients"""
        self.facebook_token = facebook_token
        self.twitter_credentials = {
            'api_key': twitter_api_key,
            'api_secret': twitter_api_secret,
            'access_token': twitter_access_token,
            'access_secret': twitter_access_secret
        }
        
        # Check which platforms are configured
        self.facebook_enabled = bool(facebook_token)
        self.twitter_enabled = all(self.twitter_credentials.values())
        
        logger.info(
            f"Social media poster initialized - "
            f"Facebook: {'enabled' if self.facebook_enabled else 'disabled'}, "
            f"Twitter: {'enabled' if self.twitter_enabled else 'disabled'}"
        )
    
    async def post_content(self, content: str) -> Dict[str, Any]:
        """
        Post content to all enabled platforms
        
        Args:
            content: Text content to post
            
        Returns:
            Dictionary with results from each platform
        """
        results = {}
        
        # Create tasks for parallel posting
        tasks = []
        
        if self.facebook_enabled:
            tasks.append(self._post_to_facebook(content))
        else:
            results['facebook'] = {
                'success': False,
                'message': 'Facebook not configured',
                'posted_at': None
            }
        
        if self.twitter_enabled:
            tasks.append(self._post_to_twitter(content))
        else:
            results['twitter'] = {
                'success': False,
                'message': 'Twitter not configured',
                'posted_at': None
            }
        
        # Execute posts in parallel
        if tasks:
            platform_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            platform_names = []
            if self.facebook_enabled:
                platform_names.append('facebook')
            if self.twitter_enabled:
                platform_names.append('twitter')
            
            for platform, result in zip(platform_names, platform_results):
                if isinstance(result, Exception):
                    logger.error(f"Error posting to {platform}: {result}")
                    results[platform] = {
                        'success': False,
                        'message': str(result),
                        'posted_at': None
                    }
                else:
                    results[platform] = result
        
        return results
    
    async def _post_to_facebook(self, content: str) -> Dict[str, Any]:
        """
        Post content to Facebook using Graph API
        
        Args:
            content: Text content to post
            
        Returns:
            Result dictionary with success status and post ID
        """
        try:
            # Facebook Graph API endpoint
            url = f"https://graph.facebook.com/v18.0/me/feed"
            
            params = {
                'message': content,
                'access_token': self.facebook_token
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        post_id = data.get('id')
                        
                        logger.info(f"Successfully posted to Facebook: {post_id}")
                        
                        return {
                            'success': True,
                            'platform': 'facebook',
                            'post_id': post_id,
                            'message': 'Posted successfully',
                            'posted_at': datetime.utcnow().isoformat()
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Facebook API error: {response.status} - {error_text}")
                        
                        return {
                            'success': False,
                            'platform': 'facebook',
                            'post_id': None,
                            'message': f"API error: {response.status}",
                            'error': error_text,
                            'posted_at': None
                        }
        
        except aiohttp.ClientError as e:
            logger.error(f"Network error posting to Facebook: {e}")
            return {
                'success': False,
                'platform': 'facebook',
                'post_id': None,
                'message': f"Network error: {str(e)}",
                'posted_at': None
            }
        except Exception as e:
            logger.error(f"Unexpected error posting to Facebook: {e}", exc_info=True)
            return {
                'success': False,
                'platform': 'facebook',
                'post_id': None,
                'message': f"Unexpected error: {str(e)}",
                'posted_at': None
            }
    
    async def _post_to_twitter(self, content: str) -> Dict[str, Any]:
        """
        Post content to X (Twitter) using API v2
        
        Args:
            content: Text content to post (max 280 characters)
            
        Returns:
            Result dictionary with success status and tweet ID
        """
        try:
            # Truncate content if too long
            if len(content) > 280:
                content = content[:277] + "..."
                logger.warning("Content truncated for Twitter (280 char limit)")
            
            # Twitter API v2 endpoint
            url = "https://api.twitter.com/2/tweets"
            
            # Prepare OAuth 1.0a headers
            headers = self._get_twitter_oauth_headers(url, 'POST')
            headers['Content-Type'] = 'application/json'
            
            payload = {
                'text': content
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 201:
                        data = await response.json()
                        tweet_id = data.get('data', {}).get('id')
                        
                        logger.info(f"Successfully posted to Twitter: {tweet_id}")
                        
                        return {
                            'success': True,
                            'platform': 'twitter',
                            'post_id': tweet_id,
                            'message': 'Posted successfully',
                            'posted_at': datetime.utcnow().isoformat()
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Twitter API error: {response.status} - {error_text}")
                        
                        return {
                            'success': False,
                            'platform': 'twitter',
                            'post_id': None,
                            'message': f"API error: {response.status}",
                            'error': error_text,
                            'posted_at': None
                        }
        
        except aiohttp.ClientError as e:
            logger.error(f"Network error posting to Twitter: {e}")
            return {
                'success': False,
                'platform': 'twitter',
                'post_id': None,
                'message': f"Network error: {str(e)}",
                'posted_at': None
            }
        except Exception as e:
            logger.error(f"Unexpected error posting to Twitter: {e}", exc_info=True)
            return {
                'success': False,
                'platform': 'twitter',
                'post_id': None,
                'message': f"Unexpected error: {str(e)}",
                'posted_at': None
            }
    
    def _get_twitter_oauth_headers(self, url: str, method: str) -> Dict[str, str]:
        """
        Generate OAuth 1.0a headers for Twitter API
        
        Note: In production, use a proper OAuth library like 'authlib' or 'requests-oauthlib'
        This is a simplified version for demonstration
        """
        import time
        import hmac
        import hashlib
        import base64
        from urllib.parse import quote
        
        # OAuth parameters
        oauth_params = {
            'oauth_consumer_key': self.twitter_credentials['api_key'],
            'oauth_nonce': base64.b64encode(str(time.time()).encode()).decode(),
            'oauth_signature_method': 'HMAC-SHA1',
            'oauth_timestamp': str(int(time.time())),
            'oauth_token': self.twitter_credentials['access_token'],
            'oauth_version': '1.0'
        }
        
        # Create signature base string
        param_string = '&'.join(
            f"{quote(k)}={quote(v)}" 
            for k, v in sorted(oauth_params.items())
        )
        
        signature_base = f"{method}&{quote(url)}&{quote(param_string)}"
        
        # Create signing key
        signing_key = (
            f"{quote(self.twitter_credentials['api_secret'])}&"
            f"{quote(self.twitter_credentials['access_secret'])}"
        )
        
        # Generate signature
        signature = base64.b64encode(
            hmac.new(
                signing_key.encode(),
                signature_base.encode(),
                hashlib.sha1
            ).digest()
        ).decode()
        
        oauth_params['oauth_signature'] = signature
        
        # Create Authorization header
        auth_header = 'OAuth ' + ', '.join(
            f'{quote(k)}="{quote(v)}"'
            for k, v in sorted(oauth_params.items())
        )
        
        return {'Authorization': auth_header}
    
    async def test_connections(self) -> Dict[str, bool]:
        """
        Test connections to all configured platforms
        
        Returns:
            Dictionary with connection status for each platform
        """
        results = {}
        
        if self.facebook_enabled:
            try:
                # Test Facebook connection
                url = "https://graph.facebook.com/v18.0/me"
                params = {'access_token': self.facebook_token}
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, params=params) as response:
                        results['facebook'] = response.status == 200
            except Exception as e:
                logger.error(f"Facebook connection test failed: {e}")
                results['facebook'] = False
        else:
            results['facebook'] = False
        
        if self.twitter_enabled:
            try:
                # Test Twitter connection
                url = "https://api.twitter.com/2/users/me"
                headers = self._get_twitter_oauth_headers(url, 'GET')
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers) as response:
                        results['twitter'] = response.status == 200
            except Exception as e:
                logger.error(f"Twitter connection test failed: {e}")
                results['twitter'] = False
        else:
            results['twitter'] = False
        
        return results


# Simulated social media poster for testing (no real API calls)
class MockSocialMediaPoster(SocialMediaPoster):
    """Mock poster for testing without real API credentials"""
    
    def __init__(self):
        super().__init__()
        self.facebook_enabled = True
        self.twitter_enabled = True
        self.posted_content = []
    
    async def _post_to_facebook(self, content: str) -> Dict[str, Any]:
        """Simulate Facebook posting"""
        await asyncio.sleep(0.1)  # Simulate network delay
        
        post_id = f"fb_{hash(content + str(datetime.utcnow()))}"
        self.posted_content.append(('facebook', content, post_id))
        
        logger.info(f"[MOCK] Posted to Facebook: {post_id}")
        
        return {
            'success': True,
            'platform': 'facebook',
            'post_id': post_id,
            'message': 'Posted successfully (mock)',
            'posted_at': datetime.utcnow().isoformat()
        }
    
    async def _post_to_twitter(self, content: str) -> Dict[str, Any]:
        """Simulate Twitter posting"""
        await asyncio.sleep(0.1)  # Simulate network delay
        
        # Truncate if needed
        if len(content) > 280:
            content = content[:277] + "..."
        
        tweet_id = f"tw_{hash(content + str(datetime.utcnow()))}"
        self.posted_content.append(('twitter', content, tweet_id))
        
        logger.info(f"[MOCK] Posted to Twitter: {tweet_id}")
        
        return {
            'success': True,
            'platform': 'twitter',
            'post_id': tweet_id,
            'message': 'Posted successfully (mock)',
            'posted_at': datetime.utcnow().isoformat()
        }


# Test function
if __name__ == "__main__":
    async def test_poster():
        poster = MockSocialMediaPoster()
        
        test_content = "Check out this amazing new feature! #AI #ContentModeration"
        
        print("\nTesting social media posting...")
        print(f"Content: {test_content}\n")
        
        results = await poster.post_content(test_content)
        
        for platform, result in results.items():
            print(f"\n{platform.upper()}:")
            print(f"  Success: {result['success']}")
            print(f"  Post ID: {result.get('post_id')}")
            print(f"  Message: {result['message']}")
    
    asyncio.run(test_poster())