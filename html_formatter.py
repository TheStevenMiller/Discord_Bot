import html
from datetime import datetime
from typing import List, Dict, Optional
import pytz
import logging

logger = logging.getLogger(__name__)


class HTMLFormatter:
    def __init__(self, timezone: str = 'America/New_York'):
        self.timezone = pytz.timezone(timezone)
    
    def format_messages(self, messages: List[Dict], channel_info: Optional[Dict] = None) -> str:
        """
        Format Discord messages into an HTML document.
        
        Args:
            messages: List of Discord message dictionaries
            channel_info: Optional channel information dictionary
            
        Returns:
            HTML string containing formatted messages
        """
        # Get current time in Eastern timezone
        now = datetime.now(self.timezone)
        timestamp_str = now.strftime('%Y-%m-%d %I:%M:%S %p %Z')
        
        # Channel information
        channel_name = channel_info.get('name', 'Unknown') if channel_info else 'Unknown'
        channel_id = channel_info.get('id', 'Unknown') if channel_info else 'Unknown'
        
        # Start building HTML
        html_parts = [
            '<!DOCTYPE html>',
            '<html>',
            '<head>',
            f'    <title>Unread Discord Messages - Channel {html.escape(str(channel_id))}</title>',
            '    <meta charset="UTF-8">',
            '    <meta name="viewport" content="width=device-width, initial-scale=1.0">',
            self._get_styles(),
            '</head>',
            '<body>',
            '    <div class="header">',
            '        <h1>Unread Messages Archive</h1>',
            f'        <p>Channel: {html.escape(channel_name)} ({html.escape(str(channel_id))})</p>',
            f'        <p>Retrieved: {html.escape(timestamp_str)}</p>',
            f'        <p class="message-count">{len(messages)} new message{"s" if len(messages) != 1 else ""}</p>',
            '    </div>',
            '    <div class="messages-container">'
        ]
        
        # Format each message
        for message in messages:
            html_parts.append(self._format_single_message(message))
        
        # Close HTML
        html_parts.extend([
            '    </div>',
            '</body>',
            '</html>'
        ])
        
        return '\n'.join(html_parts)
    
    def _format_single_message(self, message: Dict) -> str:
        """Format a single Discord message."""
        # Extract message data
        msg_id = message.get('id', 'Unknown')
        author = message.get('author', {})
        author_name = html.escape(author.get('username', 'Unknown'))
        author_discriminator = author.get('discriminator', '0000')
        content = html.escape(message.get('content', ''))
        
        # Parse timestamp
        timestamp_str = message.get('timestamp', '')
        if timestamp_str:
            try:
                # Discord timestamps are in ISO format with timezone
                dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                # Convert to Eastern timezone
                dt_eastern = dt.astimezone(self.timezone)
                formatted_time = dt_eastern.strftime('%Y-%m-%d %I:%M:%S %p %Z')
            except Exception as e:
                logger.warning(f"Failed to parse timestamp: {timestamp_str} - {e}")
                formatted_time = timestamp_str
        else:
            formatted_time = 'Unknown'
        
        # Build message HTML
        parts = [
            f'        <div class="message" data-message-id="{html.escape(str(msg_id))}">',
            '            <div class="message-header">',
            f'                <span class="author">{author_name}#{author_discriminator}</span>',
            f'                <span class="timestamp">{html.escape(formatted_time)}</span>',
            '            </div>'
        ]
        
        # Add content if present
        if content:
            # Convert line breaks to <br> tags
            formatted_content = html.escape(content).replace('\n', '<br>')
            parts.append(f'            <div class="content">{formatted_content}</div>')
        
        # Add attachments if present
        attachments = message.get('attachments', [])
        if attachments:
            parts.append('            <div class="attachments">')
            for attachment in attachments:
                parts.append(self._format_attachment(attachment))
            parts.append('            </div>')
        
        # Add embeds if present
        embeds = message.get('embeds', [])
        if embeds:
            parts.append('            <div class="embeds">')
            for embed in embeds:
                parts.append(self._format_embed(embed))
            parts.append('            </div>')
        
        parts.append('        </div>')
        
        return '\n'.join(parts)
    
    def _format_attachment(self, attachment: Dict) -> str:
        """Format a message attachment."""
        filename = html.escape(attachment.get('filename', 'Unknown'))
        url = html.escape(attachment.get('url', '#'))
        size = attachment.get('size', 0)
        
        # Format file size
        if size > 1024 * 1024:
            size_str = f"{size / (1024 * 1024):.2f} MB"
        elif size > 1024:
            size_str = f"{size / 1024:.2f} KB"
        else:
            size_str = f"{size} bytes"
        
        return f'''                <div class="attachment">
                    <span class="attachment-icon">📎</span>
                    <a href="{url}" target="_blank" rel="noopener noreferrer">{filename}</a>
                    <span class="attachment-size">({size_str})</span>
                </div>'''
    
    def _format_embed(self, embed: Dict) -> str:
        """Format a message embed."""
        parts = ['                <div class="embed">']
        
        # Title
        if 'title' in embed:
            title = html.escape(embed['title'])
            if 'url' in embed:
                url = html.escape(embed['url'])
                parts.append(f'                    <div class="embed-title"><a href="{url}" target="_blank" rel="noopener noreferrer">{title}</a></div>')
            else:
                parts.append(f'                    <div class="embed-title">{title}</div>')
        
        # Description
        if 'description' in embed:
            description = html.escape(embed['description']).replace('\n', '<br>')
            parts.append(f'                    <div class="embed-description">{description}</div>')
        
        # Fields
        fields = embed.get('fields', [])
        if fields:
            parts.append('                    <div class="embed-fields">')
            for field in fields:
                field_name = html.escape(field.get('name', ''))
                field_value = html.escape(field.get('value', '')).replace('\n', '<br>')
                inline = field.get('inline', False)
                inline_class = ' inline' if inline else ''
                parts.append(f'''                        <div class="embed-field{inline_class}">
                            <div class="embed-field-name">{field_name}</div>
                            <div class="embed-field-value">{field_value}</div>
                        </div>''')
            parts.append('                    </div>')
        
        # Footer
        if 'footer' in embed:
            footer_text = html.escape(embed['footer'].get('text', ''))
            parts.append(f'                    <div class="embed-footer">{footer_text}</div>')
        
        parts.append('                </div>')
        
        return '\n'.join(parts)
    
    def _get_styles(self) -> str:
        """Get CSS styles for the HTML document."""
        return '''    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #36393f;
            color: #dcddde;
            margin: 0;
            padding: 20px;
            line-height: 1.6;
        }
        
        .header {
            background: #2f3136;
            border-bottom: 3px solid #7289da;
            padding: 20px;
            margin: -20px -20px 20px -20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.3);
        }
        
        .header h1 {
            margin: 0 0 10px 0;
            color: #ffffff;
            font-size: 28px;
        }
        
        .header p {
            margin: 5px 0;
            color: #b9bbbe;
        }
        
        .message-count {
            color: #7289da;
            font-weight: bold;
            font-size: 18px;
        }
        
        .messages-container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .message {
            background: #40444b;
            margin: 15px 0;
            padding: 15px 20px;
            border-radius: 8px;
            border-left: 4px solid #7289da;
            transition: all 0.2s ease;
        }
        
        .message:hover {
            background: #464950;
            transform: translateX(2px);
        }
        
        .message-header {
            margin-bottom: 8px;
        }
        
        .author {
            font-weight: bold;
            color: #7289da;
            font-size: 16px;
        }
        
        .timestamp {
            color: #72767d;
            font-size: 12px;
            margin-left: 10px;
        }
        
        .content {
            color: #dcddde;
            margin-top: 8px;
            word-wrap: break-word;
        }
        
        .attachments {
            margin-top: 10px;
        }
        
        .attachment {
            background: #2f3136;
            padding: 8px 12px;
            margin: 5px 0;
            border-radius: 4px;
            display: inline-block;
        }
        
        .attachment-icon {
            margin-right: 5px;
        }
        
        .attachment a {
            color: #00b0f4;
            text-decoration: none;
        }
        
        .attachment a:hover {
            text-decoration: underline;
        }
        
        .attachment-size {
            color: #72767d;
            font-size: 12px;
            margin-left: 5px;
        }
        
        .embeds {
            margin-top: 10px;
        }
        
        .embed {
            background: #2f3136;
            padding: 12px;
            margin: 5px 0;
            border-radius: 4px;
            border-left: 4px solid #5865f2;
        }
        
        .embed-title {
            font-weight: bold;
            color: #ffffff;
            margin-bottom: 5px;
        }
        
        .embed-title a {
            color: #00b0f4;
            text-decoration: none;
        }
        
        .embed-title a:hover {
            text-decoration: underline;
        }
        
        .embed-description {
            color: #dcddde;
            margin-bottom: 10px;
        }
        
        .embed-fields {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }
        
        .embed-field {
            flex: 1 1 100%;
            min-width: 200px;
        }
        
        .embed-field.inline {
            flex: 1 1 30%;
        }
        
        .embed-field-name {
            font-weight: bold;
            color: #b9bbbe;
            margin-bottom: 2px;
        }
        
        .embed-field-value {
            color: #dcddde;
        }
        
        .embed-footer {
            color: #72767d;
            font-size: 12px;
            margin-top: 10px;
        }
        
        @media (max-width: 768px) {
            body {
                padding: 10px;
            }
            
            .header {
                margin: -10px -10px 10px -10px;
                padding: 15px;
            }
            
            .message {
                padding: 12px 15px;
            }
            
            .embed-field.inline {
                flex: 1 1 100%;
            }
        }
    </style>'''