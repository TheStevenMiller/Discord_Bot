#!/usr/bin/env python3
"""
Discord Bot Message Checker
Runs once per Cloud Build trigger to check for unread messages
"""

import sys
import os
import json
import logging
from datetime import datetime
import pytz

# Add parent directory to path for imports during local testing
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from discord_client import DiscordClient
from storage import CloudStorage
from html_formatter import HTMLFormatter
from config import (
    DISCORD_BOT_TOKEN, DISCORD_CHANNEL_ID, GCS_BUCKET_NAME,
    GCP_PROJECT_ID, TIMEZONE, LOG_LEVEL
)

# Configure logging for Cloud Logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def load_state(storage: CloudStorage) -> dict:
    """Load bot state from GCS."""
    try:
        state_json = storage.download_html("_state/bot_state.json")
        if state_json:
            return json.loads(state_json)
    except Exception as e:
        logger.warning(f"Failed to load state: {e}")
    
    return {"last_read_message_id": None}


def save_state(storage: CloudStorage, state: dict) -> bool:
    """Save bot state to GCS."""
    try:
        state_json = json.dumps(state, indent=2)
        return storage.upload_html("_state/bot_state.json", state_json)
    except Exception as e:
        logger.error(f"Failed to save state: {e}")
        return False


def main():
    """Single execution to check for unread Discord messages."""
    # Validate required environment variables
    if not DISCORD_BOT_TOKEN:
        logger.error("DISCORD_BOT_TOKEN environment variable is not set")
        sys.exit(1)
    
    if not DISCORD_CHANNEL_ID:
        logger.error("DISCORD_CHANNEL_ID environment variable is not set")
        sys.exit(1)
    
    if not GCS_BUCKET_NAME:
        logger.error("GCS_BUCKET_NAME environment variable is not set")
        sys.exit(1)
    
    try:
        # Initialize components
        logger.info("Initializing Discord bot components...")
        discord = DiscordClient(DISCORD_BOT_TOKEN)
        storage = CloudStorage(GCS_BUCKET_NAME, GCP_PROJECT_ID)
        formatter = HTMLFormatter(timezone=TIMEZONE)
        
        # Create bucket if it doesn't exist
        if not storage.create_bucket_if_not_exists():
            logger.error("Failed to create or verify bucket existence")
            sys.exit(1)
        
        # Load state
        state = load_state(storage)
        last_read_id = state.get("last_read_message_id")
        
        logger.info(f"Checking channel {DISCORD_CHANNEL_ID} for messages after ID: {last_read_id}")
        
        # Get channel info
        try:
            channel_info = discord.get_channel_info(DISCORD_CHANNEL_ID)
            logger.info(f"Connected to channel: {channel_info.get('name', 'Unknown')}")
        except Exception as e:
            logger.warning(f"Failed to get channel info: {e}")
            channel_info = None
        
        # Fetch messages
        response, messages = discord.get_channel_messages(
            channel_id=DISCORD_CHANNEL_ID,
            after=last_read_id,
            limit=100
        )
        
        # Check if we have unread messages
        if messages:
            logger.info(f"Found {len(messages)} unread messages")
            
            # Format messages to HTML
            html_content = formatter.format_messages(messages, channel_info)
            
            # Generate file path with Eastern Time in single folder
            eastern = pytz.timezone(TIMEZONE)
            now_eastern = datetime.now(eastern)
            date_str = now_eastern.strftime('%Y-%m-%d')
            time_str = now_eastern.strftime('%H-%M-%S')
            
            # Simple flat structure in Discord_Messages folder
            file_path = f"Discord_Messages/unread_messages_{DISCORD_CHANNEL_ID}_{date_str}_{time_str}.html"
            
            # Upload to GCS
            if storage.upload_html(file_path, html_content):
                logger.info(f"Successfully saved {len(messages)} messages to: {file_path}")
                
                # Update state with last message ID
                last_message_id = messages[-1]['id']
                state['last_read_message_id'] = last_message_id
                state['last_check_time'] = now_eastern.isoformat()
                state['last_message_count'] = len(messages)
                state['last_file_path'] = file_path
                
                if save_state(storage, state):
                    logger.info(f"Updated last read message ID to: {last_message_id}")
                else:
                    logger.error("Failed to save state after processing messages")
            else:
                logger.error("Failed to upload HTML file to GCS")
                sys.exit(1)
        else:
            logger.info("No unread messages found")
            
            # Update last check time in state
            eastern = pytz.timezone(TIMEZONE)
            now_eastern = datetime.now(eastern)
            state['last_check_time'] = now_eastern.isoformat()
            state['last_message_count'] = 0
            save_state(storage, state)
        
        # Log execution results for Cloud Logging (structured logging)
        log_data = {
            "message": "Message check completed",
            "labels": {
                "channel_id": DISCORD_CHANNEL_ID,
                "unread_count": len(messages),
                "file_created": bool(messages),
                "last_read_id": last_read_id,
                "new_last_read_id": state.get('last_read_message_id')
            }
        }
        
        # Output as JSON for structured logging
        print(json.dumps(log_data))
        
    except Exception as e:
        logger.error(f"Error during message check: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        # Clean up
        if 'discord' in locals():
            discord.close()


if __name__ == "__main__":
    # Support command line arguments for different modes
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # Test mode - just verify components can initialize
        logger.info("Running in test mode...")
        try:
            discord = DiscordClient(DISCORD_BOT_TOKEN or "test_token")
            storage = CloudStorage(GCS_BUCKET_NAME or "test-bucket", GCP_PROJECT_ID)
            formatter = HTMLFormatter(timezone=TIMEZONE)
            logger.info("All components initialized successfully!")
        except Exception as e:
            logger.error(f"Test mode failed: {e}")
            sys.exit(1)
    else:
        # Normal execution
        main()