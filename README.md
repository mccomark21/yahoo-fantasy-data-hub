# Yahoo Fantasy Data Hub

Automated daily extraction of fantasy sports data from Yahoo Fantasy Sports using [yfpy](https://github.com/uberfastman/yfpy). Currently supports **Fantasy Baseball (MLB)** — built to expand to other sports in the future.

A GitHub Actions workflow runs daily, pulls roster and free agent data from your active Yahoo Fantasy Baseball leagues, and commits the results as a CSV to this repository.

## Output

`data/fantasy_baseball_latest.csv` — refreshed daily with these columns:

| Column | Description |
|---|---|
| `league_name` | Yahoo Fantasy league name |
| `fantasy_team` | Fantasy team name, or "Free Agent" |
| `player_name` | Full player name |
| `mlb_team` | MLB team abbreviation (e.g. NYY, LAD) |
| `eligible_positions` | Comma-separated eligible positions |
| `primary_position` | Primary position |
| `player_status` | Injury status (IL, DTD, NA) or blank |
| `percent_owned` | % owned in the league (rostered players only) |
| `last_updated` | UTC timestamp of the data refresh |

## Setup

### 1. Create a Yahoo Developer App

1. Go to [https://developer.yahoo.com/apps/create/](https://developer.yahoo.com/apps/create/)
2. Fill in:
   - **Application Name**: anything (e.g. "Fantasy Data Hub")
   - **Application Type**: select **Installed Application**
   - **Redirect URI**: `https://localhost:8080`
   - **API Permissions**: check **Fantasy Sports — Read**
3. Click **Create App**
4. Note your **Client ID (Consumer Key)** and **Client Secret (Consumer Secret)**

### 2. One-Time Local Auth

You must run the OAuth flow once from a machine with a browser to obtain a refresh token.

```bash
# Clone this repo
git clone https://github.com/YOUR_USERNAME/yahoo-fantasy-data-hub.git
cd yahoo-fantasy-data-hub

# Install dependencies
pip install -r requirements.txt

# Create .env with your credentials (see .env.example)
cp .env.example .env
# Edit .env — fill in YAHOO_CONSUMER_KEY and YAHOO_CONSUMER_SECRET

# Run the auth setup script
python scripts/auth_setup.py
```

A browser window will open. Log in to Yahoo, authorize the app, and the script will print your **refresh token**.

### 3. Configure GitHub Secrets

In your GitHub repo, go to **Settings → Secrets and variables → Actions** and add these three **Repository secrets**:

| Secret Name | Value |
|---|---|
| `YAHOO_CONSUMER_KEY` | Your Consumer Key from step 1 |
| `YAHOO_CONSUMER_SECRET` | Your Consumer Secret from step 1 |
| `YAHOO_REFRESH_TOKEN` | The refresh token from step 2 |

### 4. Configure Leagues (Optional)

By default, the script **auto-discovers** all your active MLB leagues each run. No configuration needed.

If you want to restrict to specific leagues, edit `config.yaml`:

```yaml
league_ids:
  - "12345"
  - "67890"
```

Or run the discovery script to populate it automatically:

```bash
python scripts/discover_leagues.py
```

### 5. Verify

Trigger the workflow manually from the GitHub Actions tab (click **Run workflow**), or run locally:

```bash
python scripts/fetch_baseball_data.py
```

Check `data/fantasy_baseball_latest.csv` for results.

## How It Works

- **Schedule**: GitHub Actions runs at 8 AM UTC (4 AM ET) daily via cron
- **Auth**: Uses the stored refresh token to get a fresh access token each run (no browser needed)
- **Data**: Fetches team rosters (with player info + % owned) and scans the league player pool for free agents
- **Output**: Writes a single CSV and commits it back to the repo (only if data changed)
- **API calls**: ~60 per run for 2 leagues — well within Yahoo's rate limits

## Annual Maintenance

Yahoo refresh tokens expire after ~30 days of non-use. The daily cron keeps the token alive automatically.

At the start of each new MLB season:
- If using auto-discovery (default): nothing to do — new leagues are found automatically
- If using `config.yaml` league IDs: run `python scripts/discover_leagues.py` to update, then commit

If the token has expired (e.g. cron was disabled for 30+ days), re-run `python scripts/auth_setup.py` locally and update the `YAHOO_REFRESH_TOKEN` secret.

## Project Structure

```
├── .github/workflows/daily_refresh.yml   # Scheduled GitHub Actions workflow
├── data/
│   └── fantasy_baseball_latest.csv       # Daily output (auto-committed)
├── scripts/
│   ├── auth_setup.py                     # One-time OAuth setup (local)
│   ├── discover_leagues.py               # League discovery helper (local)
│   └── fetch_baseball_data.py            # Main data extraction pipeline
├── config.yaml                           # Optional league configuration
├── requirements.txt                      # Python dependencies
├── .env.example                          # Environment variable template
└── .gitignore
```
