# SFG Condensed Game Bot

A bot that automatically finds and delivers SF Giants condensed game highlights every morning — sent to Telegram and/or email, with a randomly selected baseball/coffee quip attached.

## How It Works

1. Queries the MLB Stats API for recent Giants games marked as `Final`
2. Checks each game's content feed for a condensed game MP4
3. Sends a Telegram message and/or email with a link to watch
4. Logs the game ID to avoid duplicate posts across runs

State is persisted by committing `posted_games.txt` back to the repo after each successful post, using the built-in `GITHUB_TOKEN`. No external storage required.

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment variables

Create a `.env` file (for local runs) or set GitHub Actions secrets:

| Variable | Description |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Token from @BotFather |
| `TELEGRAM_CHAT_ID` | Target chat or channel ID |
| `EMAIL_ADDRESS` | Gmail address to send from |
| `EMAIL_APP_PASSWORD` | Gmail app password |
| `EMAIL_RECIPIENT` | Recipient email(s), comma-separated |

Email is optional — if the email variables are not set, that delivery method is skipped.

### 3. Run

```bash
python run_bot.py
```

## Automation

The bot runs via GitHub Actions on a schedule: **every 5 minutes from 6:00–9:00 AM UK time**. This window targets when MLB condensed games are typically published after overnight games.

A second workflow (`manual_force_check.yml`) is available for manual dispatch if you need to trigger a check on demand.

## Files

| File | Purpose |
|---|---|
| `run_bot.py` | Main bot script |
| `copy_bank.json` | Pool of 500 SF Giants/San Francisco quips used in messages |
| `posted_games.txt` | Log of already-posted game IDs (committed back to repo after each post) |
