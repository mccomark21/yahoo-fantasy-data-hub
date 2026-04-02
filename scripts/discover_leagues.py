#!/usr/bin/env python3
"""Discover active Yahoo Fantasy Baseball leagues and update config.yaml.

Run this locally at the start of each new season to refresh league IDs,
or let fetch_baseball_data.py auto-discover them on each run.
"""

import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

# Load .env from project root
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

required = ["YAHOO_CONSUMER_KEY", "YAHOO_CONSUMER_SECRET", "YAHOO_REFRESH_TOKEN"]
missing = [v for v in required if not os.environ.get(v)]
if missing:
    print(f"Error: Missing environment variables: {', '.join(missing)}")
    sys.exit(1)

from yfpy.query import YahooFantasySportsQuery

token_json = {
    "access_token": "auto_refresh",
    "consumer_key": os.environ["YAHOO_CONSUMER_KEY"],
    "consumer_secret": os.environ["YAHOO_CONSUMER_SECRET"],
    "guid": "",
    "refresh_token": os.environ["YAHOO_REFRESH_TOKEN"],
    "token_time": 0.0,
    "token_type": "bearer",
}

print("Connecting to Yahoo Fantasy Sports API...")
query = YahooFantasySportsQuery(
    league_id="0",
    game_code="mlb",
    yahoo_access_token_json=token_json,
    browser_callback=False,
)

game = query.get_current_game_metadata()
print(f"Current MLB season: {game.season} (game_key: {game.game_key})")

if getattr(game, "is_offseason", 0):
    print("Note: MLB is currently in the off-season.")

leagues = query.get_user_leagues_by_game_key(game.game_key)
if not leagues:
    print("No active MLB leagues found for your account.")
    sys.exit(0)

print(f"\nFound {len(leagues)} league(s):")
league_ids = []
for league in leagues:
    league_obj = getattr(league, "league", league)
    lid = getattr(league_obj, "league_id", None)
    name = getattr(league_obj, "name", "Unknown")
    print(f"  - {name} (ID: {lid})")
    if lid:
        league_ids.append(str(lid))

# Update config.yaml
config_path = Path(__file__).resolve().parent.parent / "config.yaml"
config = {}
if config_path.exists():
    with open(config_path) as f:
        config = yaml.safe_load(f) or {}

config["league_ids"] = league_ids
config.setdefault("game_code", "mlb")
config.setdefault("free_agent_limit", 250)

with open(config_path, "w") as f:
    yaml.dump(config, f, default_flow_style=False, sort_keys=False)

print(f"\nUpdated {config_path} with {len(league_ids)} league ID(s).")
