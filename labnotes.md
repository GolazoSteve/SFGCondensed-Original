# SFGCondensed Lab Notes

## Session: 2026-03-10 — Full Audit, Refactor & Deployment

### What this bot does
Checks MLB's stats API every 5 minutes (5–9am UTC) for a new SF Giants condensed game video. When found, posts it to Telegram and/or email, then logs the game PK to Google Drive so it doesn't double-post.

---

### Bugs Fixed

**FORCE_POST never worked**
The manual workflow passed `FORCE_POST=true` as an env var but `run_bot.py` never read it. Manual force-posts were silently ignored. Fixed by reading the env var and skipping `already_posted()` when set.

**`already_posted()` false-positives**
Used raw substring match on file contents — gamePK `717` would match against logged `7177`. Fixed with `.splitlines()` for exact line matching.

**`send_email()` success flag always True**
`success = True` was set before the loop and never reset to `False`. Bot would mark a game as posted even if all emails failed. Fixed by initialising `success = False` and only setting it `True` after a confirmed send.

**Manual workflow missing Google credentials**
`manual_force_check.yml` didn't pass `GOOGLE_SERVICE_ACCOUNT_JSON` or `GOOGLE_DRIVE_FOLDER_ID`, so the bot crashed on every manual run. Also had conflicting git commit steps (Drive handles state, not git). Fixed by adding all secrets and removing the git steps.

---

### Security Fixes

**Drive folder ID was hardcoded in workflow**
`GOOGLE_DRIVE_FOLDER_ID` was a plaintext value in `breakfast_bot.yml`, public in the repo. Moved to a GitHub secret.

**Telegram request had no timeout**
A hung connection would stall the Actions runner indefinitely. Added `timeout=10`.

---

### Code Quality

- Removed unused `BeautifulSoup` import and `beautifulsoup4` from `requirements.txt`
- Fixed file handle leak on `copy_bank.json` (now uses `with open()`)
- Added try/except to `send_telegram_message()` — previously a network error would crash the bot
- Refactored SMTP to open one connection per run instead of one per recipient
- Added `fetch_with_retry()` helper (3 attempts, 2s backoff) used by all MLB API calls
- Added startup validation — exits immediately with a clear message if any required env var is missing
- Removed redundant `pip install` line from `breakfast_bot.yml` (packages already in `requirements.txt`)
- Fixed misleading cron schedule comment (now correctly states UTC with BST/GMT note)
- Added `tzdata` to `requirements.txt` for Windows timezone support (Linux/Actions has it built in)

---

### New Features

**`TEAM_ID` env var** — defaults to `137` (Giants) but now configurable without touching code.

**No-game alert** — if it's past `NO_GAME_CUTOFF_HOUR` UK time (default 9am) and no game was posted, sends a Telegram alert so you know to check manually.

**Retry logic** — transient MLB API failures now retry up to 3 times before giving up.

---

### Infrastructure

- Created `.gitignore` (`.env`, `posted_games.txt`, `__pycache__`)
- Created `.env` locally with all credentials (not committed)
- Set all 7 GitHub Actions secrets via the web UI
- Committed and pushed everything to `main` on `GolazoSteve/SFGCondensed`
- Verified end-to-end with a manual workflow trigger — Telegram message delivered successfully

---

### Credentials & Services in Use

| Service | Account |
|---|---|
| Telegram Bot | `@` via BotFather, token starting `8733526256:` |
| Telegram Chat | Personal chat with Steve (`514323668`) |
| Google Service Account | `claudesfgcondensed@innate-attic-457820-s3.iam.gserviceaccount.com` |
| Google Drive Folder | `11QV7pggur2rI0AM2cKfhAOswtFTZgM42` |
| Gmail | `stevedobbingklein@gmail.com` (App Password auth) |

---

### Outstanding / Future Ideas

- No-game alert fires on every run past cutoff — could deduplicate by tracking alert state in Drive
- Could add a weekly digest or season stats summary
- `TEAM_ID` is configurable but the "Giants" label in log output is still hardcoded

---

## Session: 2026-03-20 — SFGArchived Bot Created

### What was built
A second standalone bot at `C:\Users\Steve\DevSandbox\SFGArchived\` that posts a link to the full archived game broadcast on MLB.tv, rather than the condensed game MP4. Completely separate from this repo — nothing here was touched.

### How it works
- Same schedule API logic as SFGCondensed — finds Final Giants games in the last 7 days
- Constructs the MLB.tv archive URL: `https://www.mlb.com/tv/g{gamePk}`
- Posts `📺 Away @ Home\n{url}` to the same Telegram channel
- Tracks posted games in a local `posted_archived.txt` (no Google Drive — not needed for a locally-run bot)
- Run via `run_bot.bat` (double-click to run)
- Uses the same `.env` file (copied from SFGCondensed), only needs `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`

### Key finding during build
The MLB Stats API content endpoint does not expose full game archive URLs — only condensed game MP4s and highlight clips. Full game archives are auth-gated on MLB.tv. The `mlb.com/tv/g{gamePk}` URL loads the MLB.tv player shell and works for subscribers who are already logged in on desktop.

### Outstanding / Known Issues

- **Mobile deep-link problem**: the `mlb.com/tv/g{gamePk}` URL on mobile prompts to download the app rather than opening in-app, even if the MLB app is already installed. Need to find the correct MLB app deep-link URL scheme (e.g. `mlbatbat://` or a universal link) that hands off directly to the app
- No GitHub Actions workflow yet — currently manual/local only
- No quip/copy added to the message yet (intentionally deferred)

---

## Session: 2026-03-10 — SaaS Planning

### Decision
Keeping this repo as a personal Giants bot long-term. The SaaS version (multi-team, web signup, Supabase) will live in a separate repo: `mlb-highlights-web`.

### SaaS Architecture Decided
- **Backend state**: Supabase (PostgreSQL) replaces Google Drive file — `posted_games` and `subscriptions` tables
- **Frontend**: Next.js on Vercel (free tier) — landing page, auth (magic link), dashboard
- **Bot**: Copy of `run_bot.py` adapted to loop all 30 MLB teams, query subscribers from Supabase, send per-subscriber
- **Cron**: Same GitHub Actions schedule, but in the new repo

### Plan documented
Full phased implementation plan written to `plan.md` in this repo — covers Supabase schema SQL, Next.js directory structure, workflow changes, Telegram webhook UX, and deployment steps.

### Phases complete (in the new repo, not here)
- Phase 2 (bot refactor) and Phase 4 (workflow updates) designed and validated — ready to implement in `mlb-highlights-web`

### This repo unchanged
All files reverted to original state after exploratory edits. Personal bot continues running as-is on Google Drive state.

---

## Session: 2026-03-20 — Replace Google Drive with git-committed state

### What changed
Removed Google Drive as the state persistence mechanism. `posted_games.txt` is now committed back to the repo by the Actions runner after each successful post, using the built-in `GITHUB_TOKEN`.

### Motivation
- 4 Google dependencies (`google-api-python-client`, `google-auth`, `google-auth-httplib2`, `google-auth-oauthlib`) removed from `requirements.txt`
- 2 GitHub secrets removed (`GOOGLE_SERVICE_ACCOUNT_JSON`, `GOOGLE_DRIVE_FOLDER_ID`)
- ~40 lines of Drive boilerplate deleted from `run_bot.py` (`get_drive_service()`, `download_posted_file()`, `upload_posted_file()`)
- The workflow already checks out the repo — no external storage was ever needed

### Changes made
- `run_bot.py`: removed Google imports, Drive functions, and related `REQUIRED_ENV_VARS` entries
- `requirements.txt`: removed the four `google-*` packages
- `.gitignore`: removed `posted_games.txt` so the file is tracked by git
- Both workflows: added `permissions: contents: write`, removed `GOOGLE_*` env vars, added a git commit+push step after the bot run with `[skip ci]` to avoid triggering recursive workflow runs

### Verified
- Local test: bot ran cleanly, no Drive calls, no errors
- GHA test: manual dispatch completed in 9s, both "Run the bot with force" and "Commit posted_games.txt" steps passed

### copy_bank.json expanded
Grew the quip pool from ~237 lines to exactly 500. New lines are all SF Giants / San Francisco themed — covering the three-peat, specific players and moments (Lincecum, Cain's perfect game, MadBum Game 7, Scutaro, Pence, Belt's 21-pitch AB), broadcasters (Miller, Kruk & Kuip), Oracle Park, SF neighbourhoods, local food, and the city's baseball identity.

### Remote URL updated
Updated git remote from `GolazoSteve/SFGCondensed` (redirected) to `GolazoSteve/SFGCondensed-Original` (canonical).

### SaaS repo created
New repo `GolazoSteve/morning-lineup` at `C:\Users\Steve\DevSandbox\morning-lineup`. Contains `README.md` and `plan.md`. This is where the multi-team SaaS build (Phases 3–5) will happen — Next.js web app, Supabase, adapted Python bot.
