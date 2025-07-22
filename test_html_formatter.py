import unittest
from html_formatter import HTMLFormatter


class TestHTMLFormatter(unittest.TestCase):
    def setUp(self):
        self.formatter = HTMLFormatter()
        self.sample_message = {
            "id": "123456789",
            "content": "Hello, this is a test message!",
            "timestamp": "2024-01-15T10:30:00.000000+00:00",
            "author": {
                "username": "TestUser",
                "discriminator": "1234"
            }
        }
        self.channel_info = {
            "id": "987654321",
            "name": "test-channel"
        }
    
    def test_initialization(self):
        """Test formatter initialization with timezone."""
        formatter = HTMLFormatter(timezone='America/New_York')
        self.assertEqual(formatter.timezone.zone, 'America/New_York')
    
    def test_format_single_message(self):
        """Test formatting a single message."""
        messages = [self.sample_message]
        html = self.formatter.format_messages(messages, self.channel_info)
        
        # Check that HTML contains expected elements
        self.assertIn('<!DOCTYPE html>', html)
        self.assertIn('<html>', html)
        self.assertIn('test-channel', html)
        self.assertIn('987654321', html)
        self.assertIn('TestUser#1234', html)
        self.assertIn('Hello, this is a test message!', html)
        self.assertIn('1 new message', html)
    
    def test_format_multiple_messages(self):
        """Test formatting multiple messages."""
        messages = [
            self.sample_message,
            {
                "id": "123456790",
                "content": "Second message",
                "timestamp": "2024-01-15T10:31:00.000000+00:00",
                "author": {
                    "username": "AnotherUser",
                    "discriminator": "5678"
                }
            }
        ]
        html = self.formatter.format_messages(messages, self.channel_info)
        
        # Check for both messages
        self.assertIn('TestUser#1234', html)
        self.assertIn('AnotherUser#5678', html)
        self.assertIn('2 new messages', html)
    
    def test_format_message_with_attachment(self):
        """Test formatting a message with attachments."""
        message_with_attachment = self.sample_message.copy()
        message_with_attachment['attachments'] = [{
            'filename': 'test.png',
            'url': 'https://example.com/test.png',
            'size': 1024 * 50  # 50 KB
        }]
        
        html = self.formatter.format_messages([message_with_attachment], self.channel_info)
        
        # Check attachment formatting
        self.assertIn('test.png', html)
        self.assertIn('https://example.com/test.png', html)
        self.assertIn('50.00 KB', html)
        self.assertIn('📎', html)
    
    def test_format_message_with_embed(self):
        """Test formatting a message with embeds."""
        message_with_embed = self.sample_message.copy()
        message_with_embed['embeds'] = [{
            'title': 'Embed Title',
            'description': 'This is an embed description',
            'url': 'https://example.com',
            'fields': [
                {'name': 'Field 1', 'value': 'Value 1', 'inline': True},
                {'name': 'Field 2', 'value': 'Value 2', 'inline': False}
            ],
            'footer': {'text': 'Footer text'}
        }]
        
        html = self.formatter.format_messages([message_with_embed], self.channel_info)
        
        # Check embed formatting
        self.assertIn('Embed Title', html)
        self.assertIn('This is an embed description', html)
        self.assertIn('Field 1', html)
        self.assertIn('Value 1', html)
        self.assertIn('Footer text', html)
    
    def test_handle_missing_data(self):
        """Test handling messages with missing data."""
        incomplete_message = {
            "id": "123",
            "content": ""  # Empty content
            # Missing timestamp and author
        }
        
        html = self.formatter.format_messages([incomplete_message])
        
        # Should handle missing data gracefully
        self.assertIn('Unknown', html)  # For missing author/channel
        self.assertNotIn('class="content"', html)  # Empty content not rendered
    
    def test_html_escaping(self):
        """Test that HTML special characters are properly escaped."""
        message_with_html = self.sample_message.copy()
        message_with_html['content'] = '<script>alert("XSS")</script>'
        message_with_html['author']['username'] = 'User<script>'
        
        html = self.formatter.format_messages([message_with_html], self.channel_info)
        
        # Check that HTML is escaped
        self.assertNotIn('<script>alert("XSS")</script>', html)
        # The content is double-escaped in the HTML output
        self.assertIn('&amp;lt;script&amp;gt;alert(&amp;quot;XSS&amp;quot;)&amp;lt;/script&amp;gt;', html)
        self.assertIn('User&lt;script&gt;', html)
    
    def test_line_breaks_conversion(self):
        """Test that line breaks are converted to <br> tags."""
        message_with_breaks = self.sample_message.copy()
        message_with_breaks['content'] = 'Line 1\nLine 2\nLine 3'
        
        html = self.formatter.format_messages([message_with_breaks], self.channel_info)
        
        # Check line breaks are converted
        self.assertIn('Line 1<br>Line 2<br>Line 3', html)
    
    def test_timezone_conversion(self):
        """Test that timestamps are converted to Eastern timezone."""
        # Create formatter with Eastern timezone
        eastern_formatter = HTMLFormatter(timezone='America/New_York')
        
        # Message with UTC timestamp
        message = self.sample_message.copy()
        message['timestamp'] = '2024-01-15T15:00:00+00:00'  # 3 PM UTC
        
        html = eastern_formatter.format_messages([message], self.channel_info)
        
        # Should show as 10 AM EST (UTC-5)
        self.assertIn('10:00:00 AM', html)
    
    def test_file_size_formatting(self):
        """Test different file size formatting."""
        formatter = HTMLFormatter()
        
        # Test bytes
        small_attachment = formatter._format_attachment({
            'filename': 'small.txt',
            'url': '#',
            'size': 500
        })
        self.assertIn('500 bytes', small_attachment)
        
        # Test KB
        medium_attachment = formatter._format_attachment({
            'filename': 'medium.pdf',
            'url': '#',
            'size': 1024 * 100  # 100 KB
        })
        self.assertIn('100.00 KB', medium_attachment)
        
        # Test MB
        large_attachment = formatter._format_attachment({
            'filename': 'large.zip',
            'url': '#',
            'size': 1024 * 1024 * 5  # 5 MB
        })
        self.assertIn('5.00 MB', large_attachment)


if __name__ == '__main__':
    unittest.main()