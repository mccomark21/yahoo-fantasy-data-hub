#!/usr/bin/env python3
"""Fetch fantasy baseball rosters and free agents from Yahoo Fantasy Sports.

Outputs data/fantasy_baseball_latest.csv with player data from all active
MLB leagues. Designed to run daily via GitHub Actions or locally.
"""

import csv
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml
from dotenv import load_dotenv
from yfpy.exceptions import YahooFantasySportsDataNotFound
from yfpy.query import YahooFantasySportsQuery

# Load .env from project root
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def build_token_json():
    """Build Yahoo access token dict from environment variables."""
    return {
        "access_token": "auto_refresh",
        "consumer_key": os.environ["YAHOO_CONSUMER_KEY"],
        "consumer_secret": os.environ["YAHOO_CONSUMER_SECRET"],
        "guid": "",
        "refresh_token": os.environ["YAHOO_REFRESH_TOKEN"],
        "token_time": 0.0,
        "token_type": "bearer",
    }


def create_query(league_id, token_json):
    """Create an authenticated YahooFantasySportsQuery."""
    return YahooFantasySportsQuery(
        league_id=str(league_id),
        game_code="mlb",
        yahoo_access_token_json=token_json,
        browser_callback=False,
    )


def decode_str(value):
    """Decode byte strings returned by yfpy into proper unicode strings."""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    s = str(value) if value else ""
    if s.startswith("b'") and s.endswith("'"):
        try:
            return eval(s).decode("utf-8", errors="replace")  # noqa: S307
        except Exception:
            return s[2:-1]
    if s.startswith('b"') and s.endswith('"'):
        try:
            return eval(s).decode("utf-8", errors="replace")  # noqa: S307
        except Exception:
            return s[2:-1]
    return s


def extract_positions(eligible_positions):
    """Normalize eligible_positions to a comma-separated string."""
    if not eligible_positions:
        return ""
    if isinstance(eligible_positions, list):
        parts = []
        for pos in eligible_positions:
            if isinstance(pos, str):
                parts.append(pos)
            elif isinstance(pos, dict):
                parts.append(pos.get("position", ""))
            else:
                p = getattr(pos, "position", None)
                parts.append(str(p) if p else str(pos))
        return ",".join(p for p in parts if p)
    if isinstance(eligible_positions, dict):
        return eligible_positions.get("position", "")
    p = getattr(eligible_positions, "position", None)
    return str(p) if p else str(eligible_positions)


def extract_player(player, league_name, fantasy_team):
    """Extract a flat dict of player fields from a yfpy Player object."""
    name_obj = getattr(player, "name", None)
    if name_obj:
        player_name = getattr(name_obj, "full", None) or str(name_obj)
    else:
        player_name = ""

    mlb_team = getattr(player, "editorial_team_abbr", "") or ""

    eligible = getattr(player, "eligible_positions", None)
    eligible_positions = extract_positions(eligible)
    primary_position = getattr(player, "primary_position", "") or ""

    player_status = getattr(player, "status", "") or ""
    if not player_status:
        player_status = getattr(player, "status_full", "") or ""

    pct_obj = getattr(player, "percent_owned", None)
    if pct_obj:
        percent_owned = getattr(pct_obj, "value", "")
    else:
        percent_owned = ""

    return {
        "league_name": decode_str(league_name),
        "fantasy_team": decode_str(fantasy_team),
        "player_name": decode_str(player_name),
        "mlb_team": decode_str(mlb_team),
        "eligible_positions": eligible_positions,
        "primary_position": str(primary_position),
        "player_status": str(player_status),
        "percent_owned": str(percent_owned) if percent_owned != "" else "",
    }


def discover_leagues(token_json):
    """Auto-discover active MLB fantasy leagues for the authenticated user."""
    query = create_query("0", token_json)

    game = query.get_current_game_metadata()
    print(f"MLB season: {game.season} (game_key: {game.game_key})")

    if getattr(game, "is_offseason", 0):
        print("Warning: MLB is in the off-season. Roster data may be limited.")

    leagues = query.get_user_leagues_by_game_key(game.game_key)
    if not leagues:
        return []

    result = []
    for league in leagues:
        league_obj = getattr(league, "league", league)
        result.append(league_obj)

    print(f"Found {len(result)} active MLB league(s)")
    return result


def fetch_free_agents(query, league_name, fa_config):
    """Fetch free agents using Yahoo API filters (status=FA, position, sort)."""
    positions = fa_config["positions"]
    limit_per_pos = fa_config["limit"]
    sort = fa_config["sort"]
    sort_type = fa_config["sort_type"]
    league_key = query.get_league_key()
    batch_size = 25
    fa_players = []

    for pos in positions:
        print(f"  Fetching free agent {pos} (limit: {limit_per_pos}, "
              f"sort: {sort}/{sort_type})...")
        start = 0
        pos_count = 0

        while pos_count < limit_per_pos:
            url = (
                f"https://fantasysports.yahooapis.com/fantasy/v2/league/"
                f"{league_key}/players;"
                f"status=FA;position={pos};sort={sort};"
                f"sort_type={sort_type};start={start};count={batch_size}"
            )
            try:
                players_data = query.query(url, ["league", "players"])
            except YahooFantasySportsDataNotFound:
                break
            except Exception as e:
                print(f"  Warning: Error fetching {pos} free agents "
                      f"at offset {start}: {e}")
                break

            batch = (players_data if isinstance(players_data, list)
                     else [players_data])
            if not batch:
                break

            remaining = limit_per_pos - pos_count
            for player in batch[:remaining]:
                player_obj = getattr(player, "player", player)
                fa_players.append(
                    extract_player(player_obj, league_name, "Free Agent")
                )
                pos_count += 1

            start += len(batch)
            if len(batch) < batch_size:
                break

        print(f"    {pos}: {pos_count} free agents")

    return fa_players


def fetch_league_data(league_id, league_name, token_json, fa_config):
    """Fetch all rostered players and free agents for one league."""
    print(f"\n{'='*50}")
    print(f"League: {decode_str(league_name)} (ID: {league_id})")
    print(f"{'='*50}")

    query = create_query(league_id, token_json)

    # If we don't have a league name yet, fetch it
    if not league_name:
        metadata = query.get_league_metadata()
        league_name = decode_str(getattr(metadata, "name", f"League {league_id}"))

    all_players = []

    # --- Rostered players ---
    teams = query.get_league_teams()
    print(f"  Teams: {len(teams)}")

    for team in teams:
        team_id = getattr(team, "team_id", None)
        team_name = decode_str(getattr(team, "name", f"Team {team_id}"))

        if not team_id:
            continue

        try:
            roster = query.get_team_roster_player_info_by_week(
                str(team_id), "current"
            )
        except Exception as e:
            print(f"  Warning: Could not fetch roster for {team_name}: {e}")
            continue

        count = 0
        for player in roster:
            player_obj = getattr(player, "player", player)
            all_players.append(extract_player(player_obj, league_name, team_name))
            count += 1

        print(f"  {team_name}: {count} players")

    # --- Free agents (filtered by status=FA server-side) ---
    fa_players = fetch_free_agents(query, league_name, fa_config)
    all_players.extend(fa_players)

    print(f"  Free agents: {len(fa_players)}")
    print(f"  Total: {len(all_players)} players")
    return all_players


def main():
    # Validate environment variables
    required = ["YAHOO_CONSUMER_KEY", "YAHOO_CONSUMER_SECRET", "YAHOO_REFRESH_TOKEN"]
    missing = [v for v in required if not os.environ.get(v)]
    if missing:
        print(f"Error: Missing environment variables: {', '.join(missing)}")
        print("Set them in a .env file (local) or as GitHub Secrets (CI).")
        sys.exit(1)

    token_json = build_token_json()

    # Load config
    config_path = Path(__file__).resolve().parent.parent / "config.yaml"
    config = {}
    if config_path.exists():
        with open(config_path) as f:
            config = yaml.safe_load(f) or {}

    fa_config = {
        "positions": config.get("free_agent_positions", ["B", "P"]),
        "limit": config.get("free_agent_limit", 500),
        "sort": config.get("free_agent_sort", "AR"),
        "sort_type": config.get("free_agent_sort_type", "season"),
    }
    configured_ids = config.get("league_ids", [])

    # Resolve leagues
    if configured_ids:
        print(f"Using {len(configured_ids)} league(s) from config.yaml")
        leagues = []
        for lid in configured_ids:
            leagues.append({"league_id": str(lid), "name": None})
    else:
        print("Auto-discovering MLB leagues...")
        discovered = discover_leagues(token_json)
        if not discovered:
            print("No active MLB leagues found. Exiting.")
            sys.exit(0)
        leagues = []
        for league in discovered:
            leagues.append({
                "league_id": str(getattr(league, "league_id", league)),
                "name": getattr(league, "name", None),
            })

    # Fetch data for each league
    all_data = []
    for league_info in leagues:
        players = fetch_league_data(
            league_info["league_id"],
            league_info["name"],
            token_json,
            fa_config,
        )
        all_data.extend(players)

    if not all_data:
        print("\nNo player data collected. Exiting.")
        sys.exit(0)

    # Add timestamp
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    for row in all_data:
        row["last_updated"] = now

    # Write CSV
    output_dir = Path(__file__).resolve().parent.parent / "data"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "fantasy_baseball_latest.csv"

    fieldnames = [
        "league_name",
        "fantasy_team",
        "player_name",
        "mlb_team",
        "eligible_positions",
        "primary_position",
        "player_status",
        "percent_owned",
        "last_updated",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_data)

    print(f"\nWrote {len(all_data)} players to {output_path}")


if __name__ == "__main__":
    main()
