import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Discord Configuration
DISCORD_BOT_TOKEN = os.environ.get('DISCORD_BOT_TOKEN')
DISCORD_CHANNEL_ID = os.environ.get('DISCORD_CHANNEL_ID')

# Google Cloud Configuration
GCP_PROJECT_ID = os.environ.get('GCP_PROJECT_ID', 'instacart-creative')
GCS_BUCKET_NAME = os.environ.get('GCS_BUCKET_NAME', 'discord-messages-instacart-creative')
GOOGLE_APPLICATION_CREDENTIALS = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')

# Cloud SQL Configuration
CLOUD_SQL_CONNECTION_NAME = os.environ.get('CLOUD_SQL_CONNECTION_NAME')
DB_USER = os.environ.get('DB_USER', 'discord_bot')
DB_PASS = os.environ.get('DB_PASS')
DB_NAME = os.environ.get('DB_NAME', 'discord_bot')

# Timezone Configuration
TIMEZONE = os.environ.get('TIMEZONE', 'America/New_York')

# API Configuration
DISCORD_API_BASE_URL = 'https://discord.com/api/v10'
USER_AGENT = 'DiscordBot (https://github.com/TheStevenMiller/discord-bot, 1.0)'

# Rate Limiting Configuration
RATE_LIMIT_WARNING_THRESHOLD = 10  # Warn when less than 10 requests remaining
API_CALL_TIMEOUT = 30  # seconds

# Logging Configuration
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')