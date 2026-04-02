#!/usr/bin/env python3
"""One-time OAuth setup to obtain a Yahoo refresh token.

Run this locally after creating a Yahoo Developer app and setting
YAHOO_CONSUMER_KEY and YAHOO_CONSUMER_SECRET in your .env file.
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

consumer_key = os.environ.get("YAHOO_CONSUMER_KEY")
consumer_secret = os.environ.get("YAHOO_CONSUMER_SECRET")

if not consumer_key or not consumer_secret:
    print("Error: YAHOO_CONSUMER_KEY and YAHOO_CONSUMER_SECRET must be set.")
    print(f"Create a .env file at: {env_path}")
    print("See .env.example for the required format.")
    sys.exit(1)

from yfpy.query import YahooFantasySportsQuery

print("Starting Yahoo OAuth2 authorization...")
print("A browser window will open. Log in to Yahoo and authorize the app.\n")

try:
    query = YahooFantasySportsQuery(
        league_id="0",
        game_code="mlb",
        yahoo_consumer_key=consumer_key,
        yahoo_consumer_secret=consumer_secret,
        browser_callback=True,
    )
except SystemExit:
    print("\nAuthorization failed. Check your consumer key and secret.")
    sys.exit(1)

print("\n" + "=" * 60)
print("  Authorization successful!")
print("=" * 60)
print(f"\nYour refresh token:\n\n  {query.oauth.refresh_token}\n")
print("Add this value as a GitHub repository secret named YAHOO_REFRESH_TOKEN.")
print("Also add YAHOO_CONSUMER_KEY and YAHOO_CONSUMER_SECRET as secrets.")
print("\nFull token data (for reference):")
print(json.dumps({
    "access_token": query.oauth.access_token,
    "consumer_key": query.oauth.consumer_key,
    "consumer_secret": query.oauth.consumer_secret,
    "guid": query.oauth.guid,
    "refresh_token": query.oauth.refresh_token,
    "token_time": query.oauth.token_time,
    "token_type": query.oauth.token_type,
}, indent=2))
