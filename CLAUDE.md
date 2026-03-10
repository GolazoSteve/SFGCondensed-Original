# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Bot

```bash
pip install -r requirements.txt
python run_bot.py
```

Requires a `.env` file with:
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
- `GOOGLE_SERVICE_ACCOUNT_JSON` (full JSON string of a Google service account)
- `GOOGLE_DRIVE_FOLDER_ID`
- `EMAIL_ADDRESS`, `EMAIL_APP_PASSWORD`, `EMAIL_RECIPIENT` (comma-separated for multiple)

## Architecture

This is a single-script bot (`run_bot.py`) with no modules or subpackages. The entire logic lives in one file:

1. **State persistence via Google Drive** — `posted_games.txt` is downloaded from Drive at startup and re-uploaded after each successful post. This allows GitHub Actions (stateless) to track which games have been announced.

2. **Game discovery** — Queries `statsapi.mlb.com/api/v1/schedule` for Giants (team ID `137`) games in the last 7 days, filters for `Final` status, then checks each game's content endpoint for a condensed game MP4 playback URL.

3. **Notification** — Sends to Telegram and/or email. Only one game is posted per run (`break` after first successful post). A random quip from `copy_bank.json` is appended to each message.

## GitHub Actions

- **`breakfast_bot.yml`**: Scheduled every 5 min from 05:00–08:59 UTC. Secrets are injected as env vars; Drive is used for state (no repo commits).
- **`manual_force_check.yml`**: Manual dispatch only. Commits `posted_games.txt` back to `main` after a force post — note this workflow does a `git reset --hard origin/main` before committing, which would discard any uncommitted local state on the runner.

## Key Data Files

- **`copy_bank.json`** — Pool of ~230 baseball/coffee quips. The `lines` array is loaded once at module import time.
- **`posted_games.txt`** — Newline-separated list of MLB game PKs that have already been posted. Empty = no games posted yet.
