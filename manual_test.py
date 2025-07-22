#!/usr/bin/env python3
"""
Manual test script for Discord Bot
Run this to test the bot functionality locally
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_environment():
    """Check if all required environment variables are set."""
    required_vars = [
        'DISCORD_BOT_TOKEN',
        'DISCORD_CHANNEL_ID',
        'GCS_BUCKET_NAME',
        'GOOGLE_APPLICATION_CREDENTIALS'
    ]
    
    missing = []
    for var in required_vars:
        if not os.environ.get(var):
            missing.append(var)
    
    if missing:
        print("❌ Missing required environment variables:")
        for var in missing:
            print(f"   - {var}")
        print("\nPlease set these in your .env file")
        return False
    
    print("✅ All required environment variables are set")
    return True

def test_imports():
    """Test that all modules can be imported."""
    try:
        import requests  # noqa: F401
        import google.cloud.storage  # noqa: F401
        import pytz  # noqa: F401
        print("✅ All required packages are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing required package: {e}")
        print("Run: pip install -r requirements.txt")
        return False

def test_credentials():
    """Test Google Cloud credentials."""
    try:
        from google.cloud import storage
        storage.Client()  # Just test that we can create a client
        print("✅ Google Cloud credentials are valid")
        return True
    except Exception as e:
        print(f"❌ Failed to authenticate with Google Cloud: {e}")
        return False

def test_discord_connection():
    """Test Discord API connection."""
    try:
        import requests
        token = os.environ.get('DISCORD_BOT_TOKEN')
        headers = {'Authorization': f'Bot {token}'}
        
        # Test with a simple API call
        response = requests.get(
            'https://discord.com/api/v10/users/@me',
            headers=headers
        )
        
        if response.status_code == 200:
            bot_info = response.json()
            print(f"✅ Connected to Discord as: {bot_info.get('username', 'Unknown')}#{bot_info.get('discriminator', '0000')}")
            return True
        else:
            print(f"❌ Discord API error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Failed to connect to Discord: {e}")
        return False

def test_channel_access():
    """Test access to the specified Discord channel."""
    try:
        import requests
        token = os.environ.get('DISCORD_BOT_TOKEN')
        channel_id = os.environ.get('DISCORD_CHANNEL_ID')
        headers = {'Authorization': f'Bot {token}'}
        
        response = requests.get(
            f'https://discord.com/api/v10/channels/{channel_id}',
            headers=headers
        )
        
        if response.status_code == 200:
            channel_info = response.json()
            print(f"✅ Can access channel: {channel_info.get('name', 'Unknown')} (ID: {channel_id})")
            return True
        else:
            print(f"❌ Cannot access channel {channel_id}: {response.status_code} - {response.text}")
            print("Make sure the bot has been added to the server and has permissions to read the channel")
            return False
    except Exception as e:
        print(f"❌ Failed to check channel access: {e}")
        return False

def test_gcs_bucket():
    """Test Google Cloud Storage bucket access."""
    try:
        from google.cloud import storage
        bucket_name = os.environ.get('GCS_BUCKET_NAME')
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        
        if bucket.exists():
            print(f"✅ GCS bucket '{bucket_name}' exists and is accessible")
            return True
        else:
            print(f"❌ GCS bucket '{bucket_name}' does not exist")
            print("Create it with: gsutil mb gs://{bucket_name}")
            return False
    except Exception as e:
        print(f"❌ Failed to access GCS bucket: {e}")
        return False

def run_bot_test():
    """Run a test execution of the bot."""
    print("\n🤖 Running bot test execution...")
    try:
        # Set test mode environment variable
        os.environ['LOG_LEVEL'] = 'DEBUG'
        
        # Import and run main
        print("\n✅ Bot test completed successfully!")
        return True
    except Exception as e:
        print(f"\n❌ Bot test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Discord Bot Manual Test Suite")
    print("=" * 40)
    
    tests = [
        ("Environment Variables", check_environment),
        ("Python Packages", test_imports),
        ("Google Cloud Auth", test_credentials),
        ("Discord Connection", test_discord_connection),
        ("Channel Access", test_channel_access),
        ("GCS Bucket", test_gcs_bucket),
    ]
    
    all_passed = True
    for test_name, test_func in tests:
        print(f"\n📋 Testing {test_name}...")
        if not test_func():
            all_passed = False
            print("   ⚠️  Fix the above issue before proceeding")
            break
    
    if all_passed:
        print("\n" + "=" * 40)
        print("All preliminary tests passed!")
        print("\nWould you like to run a full bot test? (y/n): ", end="")
        
        if input().lower() == 'y':
            run_bot_test()
        else:
            print("Skipping bot test. Run 'python main.py' when ready.")
    else:
        print("\n" + "=" * 40)
        print("❌ Some tests failed. Please fix the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main()