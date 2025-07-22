import unittest
from unittest.mock import Mock, patch, MagicMock
from discord_client import DiscordClient


class TestDiscordClient(unittest.TestCase):
    def setUp(self):
        self.bot_token = "test_bot_token"
        self.client = DiscordClient(self.bot_token)
        self.channel_id = "1180259855823540225"
    
    def test_initialization(self):
        """Test that the client initializes with correct headers."""
        self.assertEqual(self.client.bot_token, self.bot_token)
        self.assertIn('Authorization', self.client.headers)
        # Should use user token format when token doesn't start with 'Bot '
        self.assertEqual(self.client.headers['Authorization'], self.bot_token)
        self.assertIn('User-Agent', self.client.headers)
    
    @patch('discord_client.requests.Session')
    def test_get_channel_messages_success(self, mock_session_class):
        """Test successful message fetching."""
        # Setup mock
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": "1", "content": "Message 1"},
            {"id": "2", "content": "Message 2"}
        ]
        mock_response.headers = {
            'X-RateLimit-Remaining': '50',
            'X-RateLimit-Reset': '1234567890'
        }
        
        mock_session.get.return_value = mock_response
        
        # Create new client to use mocked session
        client = DiscordClient(self.bot_token)
        
        # Test
        response, messages = client.get_channel_messages(self.channel_id, limit=10)
        
        # Verify
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(messages), 2)
        # Messages should be reversed (oldest first)
        self.assertEqual(messages[0]["id"], "2")
        self.assertEqual(messages[1]["id"], "1")
    
    @patch('discord_client.requests.Session')
    def test_get_channel_messages_with_after_param(self, mock_session_class):
        """Test message fetching with 'after' parameter."""
        # Setup mock
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_response.headers = {}
        
        mock_session.get.return_value = mock_response
        
        # Create new client
        client = DiscordClient(self.bot_token)
        
        # Test
        client.get_channel_messages(self.channel_id, after="123456789")
        
        # Verify the call was made with correct params
        mock_session.get.assert_called_once()
        call_args = mock_session.get.call_args
        self.assertIn('params', call_args[1])
        self.assertEqual(call_args[1]['params']['after'], "123456789")
    
    @patch('discord_client.requests.Session')
    def test_get_channel_info_success(self, mock_session_class):
        """Test successful channel info fetching."""
        # Setup mock
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": self.channel_id,
            "name": "test-channel",
            "type": 0
        }
        mock_response.headers = {}
        
        mock_session.get.return_value = mock_response
        
        # Create new client
        client = DiscordClient(self.bot_token)
        
        # Test
        channel_info = client.get_channel_info(self.channel_id)
        
        # Verify
        self.assertEqual(channel_info["id"], self.channel_id)
        self.assertEqual(channel_info["name"], "test-channel")
    
    @patch('discord_client.requests.Session')
    def test_rate_limit_warning(self, mock_session_class):
        """Test that rate limit warnings are logged."""
        # Setup mock
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_response.headers = {
            'X-RateLimit-Remaining': '5'  # Low remaining count
        }
        
        mock_session.get.return_value = mock_response
        
        # Create new client
        client = DiscordClient(self.bot_token)
        
        # Test with mock logger
        with patch('discord_client.logger') as mock_logger:
            client.get_channel_messages(self.channel_id)
            
            # Verify warning was logged
            mock_logger.warning.assert_called_once()
            warning_message = mock_logger.warning.call_args[0][0]
            self.assertIn("Rate limit warning", warning_message)
            self.assertIn("5", warning_message)
    
    def test_close(self):
        """Test that the session is properly closed."""
        with patch.object(self.client.session, 'close') as mock_close:
            self.client.close()
            mock_close.assert_called_once()


if __name__ == '__main__':
    unittest.main()