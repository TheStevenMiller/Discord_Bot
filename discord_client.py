import requests
import logging
from typing import List, Dict, Optional, Tuple
from config import DISCORD_API_BASE_URL, USER_AGENT, API_CALL_TIMEOUT

logger = logging.getLogger(__name__)


class DiscordClient:
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        # Check if this is a user token (doesn't start with 'Bot ')
        if bot_token.startswith('Bot '):
            auth_header = bot_token
        else:
            # Assume it's a user token
            auth_header = bot_token
            logger.warning("Using user token - this is against Discord ToS for automation")
        
        self.headers = {
            'Authorization': auth_header,
            'User-Agent': USER_AGENT,
            'Content-Type': 'application/json'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def get_channel_messages(
        self, 
        channel_id: str, 
        limit: int = 100,
        after: Optional[str] = None,
        before: Optional[str] = None
    ) -> Tuple[requests.Response, List[Dict]]:
        """
        Fetch messages from a Discord channel.
        
        Args:
            channel_id: The Discord channel ID
            limit: Number of messages to fetch (1-100)
            after: Get messages after this message ID
            before: Get messages before this message ID
            
        Returns:
            Tuple of (response object, list of message dictionaries)
        """
        url = f"{DISCORD_API_BASE_URL}/channels/{channel_id}/messages"
        
        params = {
            'limit': min(limit, 100)  # Discord API max is 100
        }
        
        if after:
            params['after'] = after
        if before:
            params['before'] = before
        
        logger.info(f"Fetching messages from channel {channel_id} with params: {params}")
        
        try:
            response = self.session.get(
                url, 
                params=params,
                timeout=API_CALL_TIMEOUT
            )
            
            # Log response headers for rate limit monitoring
            self._log_rate_limit_headers(response)
            
            if response.status_code == 200:
                messages = response.json()
                logger.info(f"Successfully fetched {len(messages)} messages")
                
                # Reverse messages to get chronological order (oldest first)
                # Discord returns them newest first
                messages.reverse()
                
                return response, messages
            else:
                logger.error(f"Failed to fetch messages: {response.status_code} - {response.text}")
                response.raise_for_status()
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error while fetching messages: {str(e)}")
            raise
    
    def get_channel_info(self, channel_id: str) -> Dict:
        """
        Get information about a Discord channel.
        
        Args:
            channel_id: The Discord channel ID
            
        Returns:
            Dictionary containing channel information
        """
        url = f"{DISCORD_API_BASE_URL}/channels/{channel_id}"
        
        logger.info(f"Fetching channel info for {channel_id}")
        
        try:
            response = self.session.get(url, timeout=API_CALL_TIMEOUT)
            
            self._log_rate_limit_headers(response)
            
            if response.status_code == 200:
                channel_info = response.json()
                logger.info(f"Successfully fetched channel info: {channel_info.get('name', 'Unknown')}")
                return channel_info
            else:
                logger.error(f"Failed to fetch channel info: {response.status_code} - {response.text}")
                response.raise_for_status()
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error while fetching channel info: {str(e)}")
            raise
    
    def _log_rate_limit_headers(self, response: requests.Response):
        """Log rate limit information from response headers."""
        headers = response.headers
        
        rate_limit_info = {
            'limit': headers.get('X-RateLimit-Limit'),
            'remaining': headers.get('X-RateLimit-Remaining'),
            'reset': headers.get('X-RateLimit-Reset'),
            'reset_after': headers.get('X-RateLimit-Reset-After'),
            'bucket': headers.get('X-RateLimit-Bucket'),
            'global': headers.get('X-RateLimit-Global')
        }
        
        # Only log if we have rate limit headers
        if any(rate_limit_info.values()):
            logger.debug(f"Rate limit info: {rate_limit_info}")
            
            # Warn if approaching rate limit
            remaining = headers.get('X-RateLimit-Remaining')
            if remaining and int(remaining) < 10:
                logger.warning(f"Rate limit warning: Only {remaining} requests remaining!")
    
    def close(self):
        """Close the session."""
        self.session.close()