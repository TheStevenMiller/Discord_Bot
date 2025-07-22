# Discord Bot Message Archiver

This Discord bot monitors channels for unread messages and archives them as HTML files in Google Cloud Storage.

## Features

- Polls Discord channels every 5-10 seconds for new messages
- Saves unread messages as styled HTML files
- Stores files in Google Cloud Storage organized by date
- Tracks last read message ID to avoid duplicates
- Includes message content, attachments, embeds, and metadata
- Uses Eastern Time (UTC-4/UTC-5) for timestamps

## Setup

### Prerequisites

1. Python 3.11+
2. Google Cloud Project with billing enabled
3. Discord Bot Token
4. Google Cloud service account with appropriate permissions

### Installation

1. Clone the repository:
```bash
git clone https://github.com/TheStevenMiller/discord-bot.git
cd discord-bot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create `.env` file from example:
```bash
cp .env.example .env
```

4. Configure environment variables in `.env`:
   - `DISCORD_BOT_TOKEN`: Your Discord bot token
   - `DISCORD_CHANNEL_ID`: Channel ID to monitor
   - `GCS_BUCKET_NAME`: Google Cloud Storage bucket name
   - `GOOGLE_APPLICATION_CREDENTIALS`: Path to service account JSON key

### Local Testing

1. Run in test mode to verify setup:
```bash
python main.py --test
```

2. Run a single message check:
```bash
python main.py
```

## Google Cloud Deployment

### Prerequisites
- Google Cloud SDK installed
- Project ID: `instacart-creative`
- Service account with permissions for GCS and Cloud Build

### Deployment Steps

1. Create GCS bucket (if not exists):
```bash
gsutil mb -p instacart-creative gs://discord-messages-instacart-creative
```

2. Store Discord bot token in Secret Manager:
```bash
echo -n "YOUR_DISCORD_BOT_TOKEN" | gcloud secrets create discord-bot-token \
    --data-file=- \
    --project=instacart-creative
```

3. Create Pub/Sub topic:
```bash
gcloud pubsub topics create discord-bot-trigger \
    --project=instacart-creative
```

4. Set up Cloud Build trigger:
```bash
gcloud builds triggers create pubsub \
    --name=discord-bot-message-check \
    --topic=projects/instacart-creative/topics/discord-bot-trigger \
    --build-config=cloudbuild.yaml \
    --project=instacart-creative
```

5. Create Cloud Scheduler job:
```bash
gcloud scheduler jobs create pubsub discord-message-check \
    --schedule="*/5 * * * * *" \
    --topic=discord-bot-trigger \
    --message-body='{"check":"messages"}' \
    --location=us-central1 \
    --project=instacart-creative
```

## File Structure

```
Discord_Bot/
├── main.py                 # Main entry point
├── discord_client.py       # Discord REST API client
├── storage.py              # Google Cloud Storage operations
├── html_formatter.py       # Message to HTML conversion
├── config.py               # Configuration management
├── requirements.txt        # Python dependencies
├── cloudbuild.yaml         # Cloud Build configuration
├── .env.example            # Environment variables template
├── .gitignore              # Git ignore rules
├── .gcloudignore          # Google Cloud ignore rules
└── README.md              # This file
```

## HTML Output Format

Messages are saved as HTML files with:
- Channel name and ID
- Timestamp in Eastern Time
- Message author and content
- Attachments with file sizes
- Discord embeds
- Professional styling with Discord-like appearance

Example path: `{channel_id}/2024/01/15/unread_messages_2024-01-15_14-30-45.html`

## Monitoring

View logs in Google Cloud Console:
```bash
gcloud logging read "resource.type=cloud_build" \
    --project=instacart-creative \
    --limit=50
```

Or stream logs in real-time:
```bash
gcloud logging tail "resource.type=cloud_build" \
    --project=instacart-creative
```

## Rate Limits

Discord API rate limits:
- 50 requests per second per bot
- Bot polls every 5 seconds = 12 requests/minute (well under limit)

## Security

- Discord bot token stored in Google Secret Manager
- Service account credentials use default application credentials
- No sensitive data logged
- All API errors handled gracefully

## Testing

Run unit tests:
```bash
python -m unittest discover -s . -p "test_*.py"
```

## License

Private repository - All rights reserved