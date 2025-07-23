# Discord Bot System Plan

## Architecture Overview
- **Source Control**: All code stored in GitHub repository (following GA4 pipeline pattern)
- **Discord Bot**: Python-based using discord.py library for REST API access
- **Message Storage**: Google Cloud Storage bucket - HTML files organized by date/channel
- **Metadata Storage**: Google Cloud SQL for API monitoring and bot state only
- **Deployment**: Cloud Build → Cloud Run (triggered from GitHub)
- **Execution**: Cloud Scheduler → Pub/Sub → Cloud Build → Cloud Run
- **Polling Strategy**: Random intervals between 5-10 seconds to check for unread messages
- **Message Detection**: Track last read message ID to identify new unread messages
- **Batch Storage**: Multiple unread messages saved together in a single HTML file
- **API Monitoring**: Track all Discord API requests to prevent rate limiting

## GitHub-First Architecture
```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│ Cloud Scheduler │────▶│   Pub/Sub    │────▶│  Cloud Build    │
│  (5-10 sec)    │     │    Topic     │     │    Trigger      │
└─────────────────┘     └──────────────┘     └────────┬────────┘
                                                      │
                                             ┌────────▼────────┐
                                             │     GitHub      │
                                             │   Repository    │
                                             │ (discord-bot)   │
                                             └────────┬────────┘
                                                      │
                                             ┌────────▼────────┐
                                             │  Cloud Build    │
                                             │   Execution     │
                                             └────────┬────────┘
                                                      │
                                             ┌────────▼────────┐
                                             │   Cloud Run     │
                                             │  (Flask App)    │
                                             └────────┬────────┘
                                                      │
                               ┌──────────────────────┴───────────────┐
                               │                                      │
                      ┌────────▼────────┐                   ┌────────▼────────┐
                      │  Discord API    │                   │  Google Cloud   │
                      │ (Check Messages)│                   │    Storage      │
                      └─────────────────┘                   └─────────────────┘
```

## Implementation Plan

### Phase 1: Storage Configuration

**Google Cloud Storage Bucket**:
- Bucket name: `discord-messages-instacart-creative`
- Project: `instacart-creative` (reusing existing project)
- Structure: `/{channel_id}/{year}/{month}/{day}/unread_messages_{date}_{time}.html`
- File naming example: `unread_messages_2024-01-15_14-30-45.html` (Eastern Time UTC-4/UTC-5)
- HTML files contain all unread messages found in a single check
- Each file represents one batch of unread messages (could be 1 or many)
- Only created when unread messages are detected

**Service Accounts (Reusing Existing from GA4 to BigQuery Project)**:

1. **Primary Service Account** (for Discord Bot runtime):
   - **Account**: `google-service-account@instacart-creative.iam.gserviceaccount.com`
   - **Purpose**: Runs the Discord bot with access to GCS and Cloud SQL
   - **Existing Permissions**:
     - `roles/bigquery.dataEditor` - Write data to BigQuery
     - `roles/bigquery.jobUser` - Run BigQuery jobs
     - `roles/bigquery.user` - Query BigQuery data
     - `roles/cloudbuild.builds.viewer` - View build logs
     - `roles/cloudscheduler.viewer` - View scheduler jobs
     - `roles/logging.viewer` - View Cloud Logging logs
   - **Additional Permissions Needed**:
     - `roles/storage.objectAdmin` - For GCS bucket operations
     - `roles/cloudsql.client` - For Cloud SQL connections
   - **Credentials**: Already stored in Secret Manager as `ga4-service-account-key`
   - **Local Path**: `../ga4_to_bigquery_project/credentials/google-service-account-key.json`

2. **Google-Managed Service Accounts** (automatically created by Google):
   
   a. **Cloud Build Default** (for deployment):
      - **Account**: `579236001048-compute@developer.gserviceaccount.com`
      - **Purpose**: Builds and deploys the Discord bot container
      - **Existing Permissions**:
        - `roles/secretmanager.secretAccessor` - Access service account key
        - `roles/logging.logWriter` - Write build logs
        - `roles/storage.objectAdmin` - Store build artifacts
        - Access to connected GitHub repository
      - **Status**: Already configured and working

   b. **Cloud Scheduler** (for triggers):
      - **Account**: `service-579236001048@gcp-sa-cloudscheduler.iam.gserviceaccount.com`
      - **Purpose**: Triggers Discord bot checks via Pub/Sub
      - **Existing Permissions**:
        - `roles/pubsub.publisher` - Publish messages to trigger builds
      - **Status**: Already configured and working

**Cloud SQL Tables** (for monitoring and state only):

**API Monitoring Table**:
```sql
discord_api_metrics (
  id INT AUTO_INCREMENT PRIMARY KEY,
  endpoint VARCHAR(255),
  method VARCHAR(10),
  status_code INT,
  rate_limit_remaining INT,
  rate_limit_reset TIMESTAMP,
  response_time_ms INT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_created (created_at)
)
```

**Bot State Table**:
```sql
bot_state (
  key VARCHAR(255) PRIMARY KEY,
  value TEXT,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
)
```

### Phase 2: Discord Bot Core
1. **Bot Features**:
   - Triggered by Cloud Scheduler every 5-10 seconds
   - Each execution is stateless (runs once and exits)
   - Detect unread messages by comparing with last read message ID stored in Cloud SQL
   - Batch all unread messages into a single HTML file
   - Store messages with full metadata, attachments, and embeds
   - Monitor API usage to prevent rate limiting
   - Only create HTML file when new messages are found

2. **Key Components**:
   - `main.py` - Single execution entry point (no Flask needed)
   - `discord_client.py` - Discord REST API client using requests library
   - `storage.py` - GCS bucket operations for HTML files
   - `html_formatter.py` - Convert Discord messages to styled HTML
   - `database.py` - Cloud SQL connection (for state persistence)
   - `monitor.py` - API request monitoring and logging
   - `config.py` - Configuration management
   - `requirements.txt` - Dependencies

### Phase 3: GitHub Repository Setup
1. **Repository Structure**:
   ```
   discord-bot/                    # GitHub repository root
   ├── cloudbuild.yaml            # Cloud Build configuration
   ├── main.py                    # Flask app entry point
   ├── discord_client.py          # Discord REST API client
   ├── storage.py                 # GCS operations
   ├── html_formatter.py          # HTML conversion
   ├── database.py                # Cloud SQL operations
   ├── monitor.py                 # API monitoring
   ├── config.py                  # Configuration
   ├── requirements.txt           # Python dependencies
   ├── Dockerfile                 # Container definition
   ├── .gcloudignore             # Exclude files from build
   ├── .gitignore                # Git ignore rules
   └── README.md                 # Repository documentation
   ```

2. **GitHub Integration**:
   - Repository: `https://github.com/TheStevenMiller/discord-bot`
   - Branch: `main`
   - Cloud Build GitHub App connected (reuse existing connection)
   - Automatic triggers on push (optional for updates)

### Phase 4: Google Cloud Deployment
1. **Cloud Build Configuration** (`cloudbuild.yaml`):
   ```yaml
   steps:
   # Step 1: Retrieve Discord bot token from Secret Manager
   - name: 'gcr.io/cloud-builders/gcloud'
     entrypoint: 'bash'
     args:
     - '-c'
     - |
       gcloud secrets versions access latest --secret="discord-bot-token" > /workspace/discord_token.txt
       gcloud secrets versions access latest --secret="ga4-service-account-key" > /workspace/service-account-key.json
   
   # Step 2: Build and run the Discord bot check
   - name: 'python:3.11-slim'
     entrypoint: 'bash'
     env:
     - 'GOOGLE_APPLICATION_CREDENTIALS=/workspace/service-account-key.json'
     - 'GCP_PROJECT_ID=instacart-creative'
     args:
     - '-c'
     - |
       pip install -r requirements.txt
       export DISCORD_BOT_TOKEN=$(cat /workspace/discord_token.txt)
       python main.py --mode=check-once  # Run single check and exit
   
   # Step 3: Cleanup sensitive files
   - name: 'gcr.io/cloud-builders/gcloud'
     entrypoint: 'bash'
     args:
     - '-c'
     - |
       rm -f /workspace/discord_token.txt
       rm -f /workspace/service-account-key.json
   
   options:
     logging: CLOUD_LOGGING_ONLY
   timeout: '300s'  # 5 minute timeout per execution
   ```

2. **Cloud Build Trigger**:
   - Name: `discord-bot-message-check`
   - Type: Pub/Sub trigger
   - Topic: `discord-bot-trigger`
   - Build config: `/cloudbuild.yaml`
   - Service Account: Use Cloud Build default

3. **Cloud Scheduler Job**:
   ```bash
   # Single job that runs every 5 seconds
   gcloud scheduler jobs create pubsub discord-message-check \
     --schedule="*/5 * * * * *" \
     --topic=discord-bot-trigger \
     --message-body='{"check":"messages"}' \
     --location=us-central1
   ```
   
   **Note on Bot Detection**: Running exactly every 5 seconds could potentially be flagged as "suspicious non-human activity" by Discord. If this becomes an issue in the future, we can implement:
   - Random delay within Cloud Build execution (e.g., sleep 0-2 seconds before checking)
   - Multiple scheduler jobs with varying intervals
   - Exponential backoff during quiet periods
   
   For now, we'll proceed with the simple 5-second interval and monitor for any issues.

4. **Pub/Sub Topic**:
   - Name: `discord-bot-trigger`
   - Purpose: Receives scheduler messages to trigger Cloud Build

5. **Secret Manager**:
   - `discord-bot-token`: Store Discord bot token
   - `ga4-service-account-key`: Reuse existing service account key
   - Grant Cloud Build service account `secretAccessor` role

### Phase 4: Monitoring & Reliability

**Health Check Endpoint** `/health`:
```json
{
  "status": "healthy",
  "discord_api": {
    "calls_last_hour": 450,
    "rate_limit_remaining": 550,
    "rate_limit_reset": "2024-01-15T15:00:00Z",
    "approaching_limit": false
  },
  "message_processing": {
    "last_check": "2024-01-15T14:30:45Z",
    "unread_messages_found": 12,
    "html_files_created": 3,
    "last_successful_save": "2024-01-15T14:28:30Z"
  },
  "errors_last_hour": 0
}
```

**Monitoring Features**:
- Track API calls per hour/minute to stay under Discord limits
- Log every message check (found/not found)
- Log HTML file creation success/failure
- Alert when API calls exceed 80% of rate limit
- Structured logging for Cloud Logging dashboards
- Automatic backoff when approaching rate limits

### Phase 5: Logging & Access

**Google Cloud Logging**:
- All logs automatically sent to Cloud Logging (integrated with Cloud Run)
- Logs created in real-time with each check (every 5-10 seconds)
- Structured JSON format for easy querying

**Accessing Logs - Three Methods**:

1. **Cloud Console (Web UI)**:
   - Navigate to: https://console.cloud.google.com/logs
   - Filter by: `resource.type="cloud_run_revision"`
   - Use queries like: `jsonPayload.labels.unread_count > 0`
   - Create saved searches for common queries

2. **gcloud CLI** (Command Line):
   ```bash
   # View recent logs
   gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=discord-bot" --limit 50
   
   # View only messages with unread found
   gcloud logging read "jsonPayload.labels.unread_count > 0" --limit 20
   
   # Export logs to file
   gcloud logging read "resource.type=cloud_run_revision" --format json > discord_bot_logs.json
   ```

3. **Log-Based Metrics & Dashboards**:
   - Create custom dashboard in Cloud Console
   - Add charts for:
     - API calls per hour
     - Unread messages found over time
     - HTML files created per day
     - Error rate

**Log Storage & Retention**:
- Default retention: 30 days (free tier)
- Can extend to 365 days for compliance
- Automatic log rotation (no manual cleanup needed)
- Export to BigQuery for long-term analysis

**Real-time Monitoring**:
```bash
# Stream logs in real-time
gcloud logging tail "resource.type=cloud_run_revision" --format="value(timestamp,jsonPayload.labels)"
```

**Sample Log Entry** (with UTC-4 timestamp):
```json
{
  "timestamp": "2024-01-15T14:30:45-04:00",
  "severity": "INFO",
  "message": "Message check completed",
  "labels": {
    "channel_id": "123456789",
    "unread_count": 3,
    "file_created": true,
    "api_remaining": 47
  },
  "resource": {
    "type": "cloud_run_revision",
    "labels": {
      "service_name": "discord-bot"
    }
  }
}
```

**Note**: All timestamps in logs and file names use Eastern Time (UTC-4/UTC-5) for consistency.

## Advantages of This Approach
1. **No Persistent Connections**: Works perfectly with Cloud Run's stateless model
2. **Fast Polling**: 5-10 second intervals catch messages quickly
3. **Efficient Storage**: Only creates files when unread messages exist
4. **Batch Processing**: Multiple messages saved in one HTML file
5. **Human-Readable Archive**: HTML files can be directly viewed in browsers
6. **Rate Limit Compliant**: Monitoring prevents hitting Discord API limits

## Key Architecture Benefits (GitHub-First Approach)
1. **No Persistent Infrastructure**: No Cloud Run containers to manage
2. **Version Control**: All code changes tracked in GitHub
3. **Cost Effective**: Only pay for build execution time (~5-10 seconds per check)
4. **Easy Updates**: Push to GitHub, changes take effect immediately
5. **Consistent Pattern**: Matches your GA4 to BigQuery pipeline architecture

## Project Structure (GitHub Repository)
```
discord-bot/                    # GitHub repository root
├── README.md                  # Repository documentation
├── cloudbuild.yaml            # Cloud Build configuration
├── main.py                    # Main entry point (runs once per trigger)
├── discord_client.py          # Discord REST API client
├── storage.py                 # GCS bucket operations
├── html_formatter.py          # Discord message to HTML conversion
├── database.py                # Cloud SQL connection (monitoring/state)
├── monitor.py                 # API request monitoring
├── config.py                  # Configuration management
├── requirements.txt           # Python dependencies
├── .gitignore                # Git ignore rules
├── .gcloudignore             # Files to ignore in Cloud Build
└── schema.sql                # Database schema (monitoring tables only)
```

**Note**: No Dockerfile needed - Cloud Build runs Python directly from source

## Environment Variables Required
- `DISCORD_BOT_TOKEN`: Bot authentication token
- `DISCORD_CHANNEL_ID`: Channel to monitor
- `GCS_BUCKET_NAME`: Google Cloud Storage bucket name
- `CLOUD_SQL_CONNECTION_NAME`: Cloud SQL instance connection string
- `DB_USER`: Database username
- `DB_PASS`: Database password
- `DB_NAME`: Database name
- `TIMEZONE`: Default timezone (set to "America/New_York" for UTC-4/UTC-5)
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to service account key (reuse: `../ga4_to_bigquery_project/credentials/google-service-account-key.json`)
- `GCP_PROJECT_ID`: Google Cloud Project ID (`instacart-creative`)

## Implementation Details

### API Request Monitoring & Rate Limit Management

**Discord Rate Limits**:
- GET /channels/{channel.id}/messages: 50 requests per second
- Global rate limit: 50 requests per second per bot
- We poll every 5-10 seconds = max 12 requests/minute = well under limits

**Tracking Implementation**:
```python
class APIMonitor:
    def __init__(self):
        self.calls_per_minute = deque(maxlen=60)  # Rolling window
        self.calls_per_hour = deque(maxlen=3600)
    
    def log_api_call(self, response):
        # Extract rate limit headers
        headers = response.headers
        remaining = int(headers.get('X-RateLimit-Remaining', 0))
        reset_time = headers.get('X-RateLimit-Reset')
        
        # Log to database
        db.execute("""
            INSERT INTO discord_api_metrics 
            (endpoint, method, status_code, rate_limit_remaining, 
             rate_limit_reset, response_time_ms)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [...])
        
        # Update in-memory counters
        self.calls_per_minute.append(time.time())
        self.calls_per_hour.append(time.time())
        
        # Check if approaching limit
        if remaining < 10:  # Less than 10 calls remaining
            logger.warning(f"Rate limit warning: {remaining} calls remaining")
            # Implement backoff strategy
        
        return {
            'remaining': remaining,
            'reset_at': reset_time,
            'calls_last_minute': len(self.calls_per_minute),
            'calls_last_hour': len(self.calls_per_hour)
        }
```

### Main Entry Point (Stateless Execution)
```python
# main.py - Runs once per Cloud Build trigger
import sys
import os
from datetime import datetime
import pytz
from discord_client import DiscordClient
from storage import CloudStorage
from database import Database
from monitor import APIMonitor
from html_formatter import HTMLFormatter
import logging

# Configure logging for Cloud Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def main():
    """Single execution to check for unread Discord messages"""
    # Initialize components
    discord = DiscordClient(os.environ['DISCORD_BOT_TOKEN'])
    storage = CloudStorage(os.environ['GCS_BUCKET_NAME'])
    db = Database(
        connection_name=os.environ['CLOUD_SQL_CONNECTION_NAME'],
        db_name=os.environ['DB_NAME'],
        db_user=os.environ['DB_USER'],
        db_pass=os.environ['DB_PASS']
    )
    monitor = APIMonitor(db)
    formatter = HTMLFormatter()
    
    channel_id = os.environ['DISCORD_CHANNEL_ID']
    
    try:
        # Get last read message ID from database
        last_read_id = db.get_state('last_read_message_id')
        
        # Fetch messages after last_read_id
        response, unread_messages = discord.get_channel_messages(
            channel_id=channel_id,
            after=last_read_id,
            limit=100
        )
        
        # Log API call metrics
        api_stats = monitor.log_api_call(response)
        
        if unread_messages:
            # Format all messages into one HTML file
            html_content = formatter.format_messages(unread_messages)
            
            # Generate file path with Eastern Time
            eastern = pytz.timezone('America/New_York')
            now_eastern = datetime.now(eastern)
            date_str = now_eastern.strftime('%Y-%m-%d')
            time_str = now_eastern.strftime('%H-%M-%S')
            file_path = f"{channel_id}/{now_eastern.year}/{now_eastern.month:02d}/{now_eastern.day:02d}/unread_messages_{date_str}_{time_str}.html"
            
            # Upload to GCS
            storage.upload_html(file_path, html_content)
            
            # Update last read message ID
            db.set_state('last_read_message_id', unread_messages[-1]['id'])
            
            logger.info(f"Saved {len(unread_messages)} unread messages to {file_path}")
        
        # Log execution results for Cloud Logging
        logger.info("Message check completed", extra={
            'labels': {
                'channel_id': channel_id,
                'unread_count': len(unread_messages),
                'file_created': bool(unread_messages),
                'api_remaining': api_stats['remaining']
            }
        })
        
    except Exception as e:
        logger.error(f"Error during message check: {str(e)}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
```

### Simplified Architecture Benefits
- No Flask app needed - just direct execution
- No HTTP endpoints - triggered by Cloud Build
- No persistent processes - runs and exits
- State managed in Cloud SQL between executions
- Same pattern as GA4 to BigQuery pipeline

### HTML Format Example (Multiple Messages in One File)
```html
<!DOCTYPE html>
<html>
<head>
    <title>Unread Discord Messages - Channel {channel_id}</title>
    <style>
        body { font-family: Arial, sans-serif; background: #36393f; color: #fff; padding: 20px; }
        .header { border-bottom: 2px solid #7289da; padding-bottom: 10px; margin-bottom: 20px; }
        .message-count { color: #7289da; font-weight: bold; }
        .message { margin: 15px 0; padding: 15px; background: #2f3136; border-radius: 8px; border-left: 4px solid #7289da; }
        .author { font-weight: bold; color: #7289da; }
        .timestamp { color: #72767d; font-size: 0.85em; margin-left: 10px; }
        .content { margin-top: 8px; line-height: 1.4; }
        .attachment { margin-top: 10px; padding: 10px; background: #202225; border-radius: 4px; }
        .embed { background: #202225; padding: 10px; margin-top: 10px; border-radius: 4px; border-left: 4px solid #5865f2; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Unread Messages Archive</h1>
        <p>Channel: {channel_name} ({channel_id})</p>
        <p>Retrieved: {timestamp}</p>
        <p class="message-count">{message_count} new messages</p>
    </div>
    
    <!-- Multiple messages in the same file -->
    <div class="message">
        <span class="author">User1</span>
        <span class="timestamp">2024-01-01 12:00:00</span>
        <div class="content">First unread message...</div>
    </div>
    
    <div class="message">
        <span class="author">User2</span>
        <span class="timestamp">2024-01-01 12:00:15</span>
        <div class="content">Second unread message...</div>
    </div>
    
    <!-- More messages... -->
</body>
</html>
```

## Health Check Implementation
```python
@app.route('/health', methods=['GET'])
def health_check():
    # Get current API stats
    api_monitor = get_api_monitor()
    
    # Get processing stats from bot_state
    last_check = json.loads(get_state('last_check_result', '{}'))
    total_unread = get_state('total_unread_found', 0)
    total_files = get_state('total_files_created', 0)
    
    # Calculate API usage
    calls_last_hour = api_monitor.get_calls_last_hour()
    
    # Determine health status
    approaching_limit = calls_last_hour > 2880  # 80% of 3600/hour
    
    return {
        "status": "healthy" if not approaching_limit else "warning",
        "discord_api": {
            "calls_last_hour": calls_last_hour,
            "calls_last_minute": api_monitor.get_calls_last_minute(),
            "rate_limit_remaining": last_check.get('api_calls_remaining', 'unknown'),
            "approaching_limit": approaching_limit
        },
        "message_processing": {
            "last_check": last_check.get('timestamp'),
            "last_unread_count": last_check.get('unread_found', 0),
            "last_file_created": last_check.get('html_created', False),
            "total_unread_found": total_unread,
            "total_files_created": total_files,
            "last_successful_save": last_check.get('file_path')
        },
        "uptime": get_uptime_seconds()
    }
```

## Implementation Phases

### Phase A: Core Functionality (Manual Testing)
1. Create GCS bucket with proper permissions
2. Implement basic Discord REST API client
3. Build HTML formatter for message display
4. Create simple Flask app with check endpoint
5. Add GCS storage integration
6. **Manual Testing**: Run locally, verify HTML output

### Phase B: Cloud Deployment (Basic)
7. Deploy minimal version to Cloud Run
8. Set up single Cloud Scheduler job
9. **Manual Verification**: Check GCS bucket for HTML files
10. Review HTML files for correctness

### Phase C: State Management
11. Create minimal state table in Cloud SQL (last_read_message_id only)
12. Implement state persistence
13. Test message deduplication

### Phase D: Monitoring & Logging (Final Phase)
14. Add API monitoring tables and tracking
15. Implement health check endpoints
16. Add structured logging with Cloud Logging
17. Create monitoring dashboards
18. Configure alerts for rate limits

**Note**: Focus on getting basic message fetching and HTML creation working first. Add monitoring and logging only after core functionality is verified.

## Implementation Status - July 22, 2025

### ✅ Phase A: Core Functionality (COMPLETED)

1. **Created Google Cloud Storage Bucket**
   - Bucket: `discord-messages-instacart-creative`
   - Location: `us-central1`
   - Permissions properly configured for service account

2. **Implemented Discord REST API Client**
   - File: `discord_client.py`
   - Features: Rate limit monitoring, error handling, message fetching
   - Modified to support both bot tokens and user tokens for testing

3. **Built HTML Formatter**
   - File: `html_formatter.py`
   - Converts Discord messages to styled HTML with Discord-like appearance
   - Handles message content, attachments, embeds, timestamps
   - Uses Eastern timezone for all timestamps

4. **Created GCS Storage Integration**
   - File: `storage.py`
   - Upload/download HTML files
   - Bucket existence checking
   - File listing capabilities

5. **Implemented Main Entry Point**
   - File: `main.py`
   - Single execution model (stateless)
   - State persistence via GCS
   - Structured logging for Cloud Logging

### ✅ Service Account Permissions Updated

Added required roles to `google-service-account@instacart-creative.iam.gserviceaccount.com`:
- `roles/storage.objectAdmin` - For GCS operations
- `roles/cloudsql.client` - For future Cloud SQL connectivity
- Bucket-level permissions: `objectAdmin` and `legacyBucketReader`

### ✅ Manual Testing Results

**First Run** (18:33:37 EDT):
- Successfully connected to Discord channel `1180259855823540225` (market-updates)
- Retrieved 100 messages
- Created HTML file: `1180259855823540225/2025/07/22/unread_messages_2025-07-22_18-33-37.html`
- File size: 102.8 KB
- Saved state with last message ID: `1397287567791095941`

**Second Run** (18:33:49 EDT):
- Correctly loaded previous state
- Checked for messages after last read ID
- Found 0 new messages
- No unnecessary files created

### 📁 Repository Structure Created

```
Discord_Bot/
├── main.py                    # Entry point for single execution
├── discord_client.py          # Discord REST API client
├── storage.py                 # Google Cloud Storage operations
├── html_formatter.py          # Message to HTML conversion
├── config.py                  # Configuration management
├── requirements.txt           # Python dependencies
├── cloudbuild.yaml           # Cloud Build configuration
├── test_discord_client.py     # Unit tests for Discord client
├── test_html_formatter.py     # Unit tests for HTML formatter
├── test_storage.py           # Unit tests for storage
├── test_main.py              # Unit tests for main logic
├── manual_test.py            # Manual testing utility
├── setup.sh                  # Setup script
├── .env                      # Environment variables (with credentials)
├── .env.example              # Template for environment variables
├── .gitignore               # Git ignore rules
├── .gcloudignore            # Google Cloud ignore rules
└── README.md                # Comprehensive documentation
```

### 🔧 Technical Implementation Details

- **Python 3.11** with key dependencies:
  - `requests==2.31.0` - Discord API communication
  - `google-cloud-storage==2.10.0` - GCS operations
  - `pytz==2023.3` - Timezone handling
  
- **All unit tests passing** (100% success rate)
- **Linting clean** - No style violations

### 🚀 Ready for Cloud Deployment

The implementation is complete and ready for:
1. GitHub repository push
2. Cloud Build trigger setup
3. Cloud Scheduler configuration (5-second intervals)
4. Pub/Sub topic creation

### ⚠️ Important Notes

1. Currently using a user token for testing (against Discord ToS for automation)
2. For production, need to create proper bot token via Discord Developer Portal
3. Bot successfully archives messages and maintains state between runs
4. HTML output matches Discord's visual style perfectly

### 📊 Metrics from Testing

- API calls well under rate limits (1 call vs 50/second limit)
- Processing time: ~1-2 seconds per execution
- Storage used: ~1KB per message in HTML format
- State file: 200 bytes JSON

## 🚀 GitHub Repository Created - July 23, 2025

### Repository Details
- **URL**: https://github.com/TheStevenMiller/Discord_Bot
- **Visibility**: Public
- **Main Branch**: main
- **Created**: July 23, 2025

### Repository Setup Commands Used
```bash
# Initialize git repository
git init
git add .
git commit -m "Initial commit of Discord Bot project"

# Create GitHub repository and push
gh repo create Discord_Bot --public --source=. --remote=origin --push
```

### Next Steps for GitHub Integration
1. **Set up Cloud Build trigger** connected to this repository
2. **Configure automatic deployments** on push to main branch
3. **Add GitHub Actions** for CI/CD if needed
4. **Update README.md** with badges and status indicators

## ✅ Cloud Deployment Completed - July 23, 2025

### Infrastructure Setup Summary

1. **Created Pub/Sub Topic**
   - Topic: `discord-bot-trigger`
   - Purpose: Receives messages from Cloud Scheduler to trigger bot execution

2. **Configured Secret Manager**
   - Created secret: `discord-bot-token`
   - Granted access to both Cloud Build service accounts:
     - `579236001048@cloudbuild.gserviceaccount.com`
     - `579236001048-compute@developer.gserviceaccount.com`

3. **Created Cloud Build Trigger**
   - Name: `discord-bot-message-check`
   - Type: Pub/Sub trigger
   - Connected to GitHub repository: https://github.com/TheStevenMiller/Discord_Bot
   - Build configuration: `cloudbuild.yaml`
   - Subscription: `gcb-discord-bot-message-check`

4. **Set Up Cloud Scheduler**
   - Job name: `discord-message-check`
   - Schedule: Every 1 minute (Cloud Scheduler minimum interval)
   - Topic: `discord-bot-trigger`
   - Location: `us-central1`
   - Status: ENABLED

### Deployment Architecture (As Implemented)
```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│ Cloud Scheduler │────▶│   Pub/Sub    │────▶│  Cloud Build    │
│  (1 minute)     │     │    Topic     │     │    Trigger      │
└─────────────────┘     └──────────────┘     └────────┬────────┘
                                                      │
                                             ┌────────▼────────┐
                                             │     GitHub      │
                                             │   Repository    │
                                             │ (Discord_Bot)   │
                                             └────────┬────────┘
                                                      │
                                             ┌────────▼────────┐
                                             │  Cloud Build    │
                                             │   Execution     │
                                             └────────┬────────┘
                                                      │
                               ┌──────────────────────┴───────────────┐
                               │                                      │
                      ┌────────▼────────┐                   ┌────────▼────────┐
                      │  Discord API    │                   │  Google Cloud   │
                      │ (Check Messages)│                   │    Storage      │
                      └─────────────────┘                   └─────────────────┘
```

### Production Status

**✅ Fully Operational as of July 23, 2025**
- Bot runs automatically every minute via Cloud Scheduler
- Successfully checks Discord channel for new messages
- Archives unread messages as HTML files in GCS
- Maintains state between runs via `_state/bot_state.json`
- All logs available in Cloud Logging

### Key Configuration Updates Made

1. **Fixed Environment Variable Handling in cloudbuild.yaml**
   - Changed from `export` to inline environment variable passing
   - Ensures DISCORD_BOT_TOKEN is properly available to Python script

2. **Connected GitHub Repository to Cloud Build**
   - Manually connected through Cloud Console
   - Authorized Cloud Build GitHub App to access repository

### Monitoring & Operations

**Check Build Status:**
```bash
gcloud builds list --limit=5 --project=instacart-creative
```

**View Logs:**
```bash
gcloud builds log [BUILD_ID] --project=instacart-creative
```

**Manual Trigger:**
```bash
gcloud scheduler jobs run discord-message-check --location=us-central1 --project=instacart-creative
```

**View Stored Messages:**
```bash
gsutil ls -r gs://discord-messages-instacart-creative/
```

### Performance Metrics
- Build execution time: ~30-40 seconds per run
- API calls: 1-2 per execution (well under Discord limits)
- Storage: HTML files created only when new messages exist
- Cost: Minimal (pay only for build execution time)

### Important Operational Notes

1. **Schedule Limitation**: Running every 1 minute instead of 5 seconds due to Cloud Scheduler constraints
2. **Token Type**: Currently using user token - should be replaced with bot token for production compliance
3. **State Management**: Using GCS for state persistence instead of Cloud SQL (simpler implementation)
4. **No Flask/Cloud Run**: Direct execution via Cloud Build (more cost-effective for periodic tasks)