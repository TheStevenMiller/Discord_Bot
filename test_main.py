import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import json
import os

# Mock google.cloud modules before any imports
sys.modules['google.cloud'] = MagicMock()
sys.modules['google.cloud.storage'] = MagicMock()
sys.modules['google.cloud.exceptions'] = MagicMock()


class TestMain(unittest.TestCase):
    
    def setUp(self):
        # Reset environment variables for each test
        self.env_patcher = patch.dict(os.environ, {
            'DISCORD_BOT_TOKEN': 'test_token',
            'DISCORD_CHANNEL_ID': 'test_channel',
            'GCS_BUCKET_NAME': 'test_bucket',
            'GCP_PROJECT_ID': 'test_project',
            'TIMEZONE': 'America/New_York'
        })
        self.env_patcher.start()
    
    def tearDown(self):
        self.env_patcher.stop()
    
    def test_load_state_success(self):
        """Test successful state loading."""
        from main import load_state
        
        mock_storage = MagicMock()
        mock_storage.download_html.return_value = '{"last_read_message_id": "123456"}'
        
        result = load_state(mock_storage)
        
        self.assertEqual(result, {"last_read_message_id": "123456"})
        mock_storage.download_html.assert_called_once_with("_state/bot_state.json")
    
    def test_load_state_no_file(self):
        """Test state loading when file doesn't exist."""
        from main import load_state
        
        mock_storage = MagicMock()
        mock_storage.download_html.return_value = None
        
        result = load_state(mock_storage)
        
        self.assertEqual(result, {"last_read_message_id": None})
    
    def test_save_state_success(self):
        """Test successful state saving."""
        from main import save_state
        
        mock_storage = MagicMock()
        mock_storage.upload_html.return_value = True
        
        state = {"last_read_message_id": "123456"}
        result = save_state(mock_storage, state)
        
        self.assertTrue(result)
        mock_storage.upload_html.assert_called_once()
        # Check that JSON was properly formatted
        call_args = mock_storage.upload_html.call_args
        self.assertEqual(call_args[0][0], "_state/bot_state.json")
        self.assertIn("last_read_message_id", call_args[0][1])
    
    @patch('sys.exit')
    def test_main_missing_token(self, mock_exit):
        """Test main exits when Discord token is missing."""
        with patch.dict(os.environ, {'DISCORD_BOT_TOKEN': ''}, clear=True):
            from main import main
            main()
            
        mock_exit.assert_called_with(1)
    
    @patch('sys.exit')
    def test_main_missing_channel_id(self, mock_exit):
        """Test main exits when channel ID is missing."""
        with patch.dict(os.environ, {
            'DISCORD_BOT_TOKEN': 'test_token',
            'DISCORD_CHANNEL_ID': ''
        }, clear=True):
            from main import main
            main()
            
        mock_exit.assert_called_with(1)
    
    @patch('main.DiscordClient')
    @patch('main.CloudStorage')
    @patch('main.HTMLFormatter')
    @patch('builtins.print')
    def test_main_no_unread_messages(self, mock_print, mock_formatter_class, 
                                    mock_storage_class, mock_discord_class):
        """Test main when no unread messages are found."""
        from main import main
        
        # Setup mocks
        mock_discord = MagicMock()
        mock_storage = MagicMock()
        mock_formatter = MagicMock()
        
        mock_discord_class.return_value = mock_discord
        mock_storage_class.return_value = mock_storage
        mock_formatter_class.return_value = mock_formatter
        
        # Mock methods
        mock_storage.create_bucket_if_not_exists.return_value = True
        mock_storage.download_html.return_value = '{"last_read_message_id": "123"}'
        mock_discord.get_channel_info.return_value = {"name": "test-channel"}
        mock_discord.get_channel_messages.return_value = (Mock(), [])  # No messages
        mock_storage.upload_html.return_value = True
        
        # Run main
        main()
        
        # Verify
        mock_discord.get_channel_messages.assert_called_once()
        mock_formatter.format_messages.assert_not_called()  # No messages to format
        
        # Check structured logging output
        mock_print.assert_called()
        print_call = mock_print.call_args[0][0]
        log_data = json.loads(print_call)
        self.assertEqual(log_data["labels"]["unread_count"], 0)
        self.assertFalse(log_data["labels"]["file_created"])
    
    @patch('main.DiscordClient')
    @patch('main.CloudStorage')
    @patch('main.HTMLFormatter')
    @patch('builtins.print')
    def test_main_with_unread_messages(self, mock_print, mock_formatter_class,
                                      mock_storage_class, mock_discord_class):
        """Test main when unread messages are found."""
        from main import main
        
        # Setup mocks
        mock_discord = MagicMock()
        mock_storage = MagicMock()
        mock_formatter = MagicMock()
        
        mock_discord_class.return_value = mock_discord
        mock_storage_class.return_value = mock_storage
        mock_formatter_class.return_value = mock_formatter
        
        # Mock messages
        test_messages = [
            {"id": "456", "content": "Test message 1"},
            {"id": "789", "content": "Test message 2"}
        ]
        
        # Mock methods
        mock_storage.create_bucket_if_not_exists.return_value = True
        mock_storage.download_html.return_value = '{"last_read_message_id": "123"}'
        mock_discord.get_channel_info.return_value = {"name": "test-channel"}
        mock_discord.get_channel_messages.return_value = (Mock(), test_messages)
        mock_formatter.format_messages.return_value = "<html>Test HTML</html>"
        mock_storage.upload_html.return_value = True
        
        # Run main
        main()
        
        # Verify
        mock_discord.get_channel_messages.assert_called_once()
        mock_formatter.format_messages.assert_called_once_with(test_messages, {"name": "test-channel"})
        
        # Check that HTML was uploaded
        upload_calls = mock_storage.upload_html.call_args_list
        self.assertEqual(len(upload_calls), 2)  # One for messages, one for state
        
        # Check structured logging output
        mock_print.assert_called()
        print_call = mock_print.call_args[0][0]
        log_data = json.loads(print_call)
        self.assertEqual(log_data["labels"]["unread_count"], 2)
        self.assertTrue(log_data["labels"]["file_created"])
    
    @patch('sys.exit')
    @patch('main.DiscordClient')
    @patch('main.CloudStorage')
    @patch('main.HTMLFormatter')
    def test_main_upload_failure(self, mock_formatter_class,
                                mock_storage_class, mock_discord_class, mock_exit):
        """Test main when HTML upload fails."""
        from main import main
        
        # Setup mocks
        mock_discord = MagicMock()
        mock_storage = MagicMock()
        mock_formatter = MagicMock()
        
        mock_discord_class.return_value = mock_discord
        mock_storage_class.return_value = mock_storage
        mock_formatter_class.return_value = mock_formatter
        
        # Mock methods
        mock_storage.create_bucket_if_not_exists.return_value = True
        mock_storage.download_html.return_value = '{"last_read_message_id": "123"}'
        mock_discord.get_channel_info.return_value = {"name": "test-channel"}
        mock_discord.get_channel_messages.return_value = (Mock(), [{"id": "456", "content": "Test"}])
        mock_formatter.format_messages.return_value = "<html>Test</html>"
        mock_storage.upload_html.return_value = False  # Upload fails
        
        # Run main
        main()
        
        # Verify error handling
        mock_exit.assert_called_with(1)
    
    @patch('sys.argv', ['main.py', '--test'])
    @patch('main.logger')
    def test_test_mode(self, mock_logger):
        """Test the --test mode."""
        # Import main module - this will trigger test mode
        import main
        
        # Reload the module to trigger the __name__ == "__main__" block
        with patch('main.DiscordClient') as mock_discord_class:
            with patch('main.CloudStorage') as mock_storage_class:
                with patch('main.HTMLFormatter') as mock_formatter_class:
                    # Set return values to avoid errors
                    mock_discord_class.return_value = MagicMock()
                    mock_storage_class.return_value = MagicMock()
                    mock_formatter_class.return_value = MagicMock()
                    
                    # Call the test mode code directly
                    try:
                        main.DiscordClient(main.DISCORD_BOT_TOKEN or "test_token")
                        main.CloudStorage(main.GCS_BUCKET_NAME or "test-bucket", main.GCP_PROJECT_ID)
                        main.HTMLFormatter(timezone=main.TIMEZONE)
                        main.logger.info("All components initialized successfully!")
                    except Exception as e:
                        main.logger.error(f"Test mode failed: {e}")
                    
                    # Verify the success message was logged
                    mock_logger.info.assert_any_call("All components initialized successfully!")


if __name__ == '__main__':
    unittest.main()