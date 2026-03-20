import requests
import os
import json
import random
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
from zoneinfo import ZoneInfo
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dateutil.parser import parse

load_dotenv()

# Startup validation
REQUIRED_ENV_VARS = [
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
]
missing = [v for v in REQUIRED_ENV_VARS if not os.getenv(v)]
if missing:
    print(f"❌ Missing required env vars: {', '.join(missing)}")
    exit(1)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
POSTED_GAMES_FILE = "posted_games.txt"
TEAM_ID = int(os.getenv("TEAM_ID", "137"))
FORCE_POST = os.getenv("FORCE_POST", "false").lower() == "true"
NO_GAME_CUTOFF_HOUR = int(os.getenv("NO_GAME_CUTOFF_HOUR", "9"))  # UK time

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")
EMAIL_RECIPIENT = os.getenv("EMAIL_RECIPIENT")

with open("copy_bank.json") as f:
    COPY_LINES = json.load(f)['lines']

def get_recent_gamepks(team_id=137):
    now_uk = datetime.now(ZoneInfo("Europe/London"))
    start_date = (now_uk - timedelta(days=7)).strftime("%Y-%m-%d")
    end_date = (now_uk + timedelta(days=1)).strftime("%Y-%m-%d")
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&teamId={team_id}&startDate={start_date}&endDate={end_date}"
    res = fetch_with_retry(url, timeout=10)
    if res is None:
        print("❌ Could not fetch MLB schedule")
        return []
    data = res.json()
    games = []
    for date in data["dates"]:
        for game in date["games"]:
            if game["status"]["detailedState"] == "Final":
                game_pk = game["gamePk"]
                game_date = game["gameDate"]
                games.append((parse(game_date), game_pk))
    games.sort(reverse=True)
    return [pk for date, pk in games]

def already_posted(gamepk):
    if not os.path.exists(POSTED_GAMES_FILE):
        return False
    with open(POSTED_GAMES_FILE, "r") as f:
        return str(gamepk) in f.read().splitlines()

def mark_as_posted(gamepk):
    with open(POSTED_GAMES_FILE, "a") as f:
        f.write(f"{gamepk}\n")

def fetch_with_retry(url, retries=3, backoff=2, **kwargs):
    for attempt in range(retries):
        try:
            res = requests.get(url, **kwargs)
            if res.status_code == 200:
                return res
            print(f"⚠️ HTTP {res.status_code} for {url} (attempt {attempt + 1})")
        except Exception as e:
            print(f"⚠️ Request error: {e} (attempt {attempt + 1})")
        if attempt < retries - 1:
            time.sleep(backoff)
    return None

def find_condensed_game(gamepk):
    url = f"https://statsapi.mlb.com/api/v1/game/{gamepk}/content"
    print(f"🔍 Checking MLB content API: {url}")
    res = fetch_with_retry(url, timeout=10)
    if res is None:
        print(f"❌ Failed to fetch content for {gamepk}")
        return None, None
    data = res.json()
    items = data.get("highlights", {}).get("highlights", {}).get("items", [])
    for item in items:
        title = item.get("title", "").lower()
        desc = item.get("description", "").lower()
        if "condensed" in title or "condensed" in desc:
            for playback in item.get("playbacks", []):
                if "mp4" in playback.get("name", "").lower():
                    return item["title"], playback["url"]
    return None, None

def send_telegram_message(title, url):
    game_info = title.replace("Condensed Game: ", "").strip()
    message = (
        f"<b>📼 {game_info}</b>\n"
        f"<code>────────────────────────────</code>\n"
        f"🎥 <a href=\"{url}\">▶ Watch Condensed Game</a>\n\n"
        f"<i>{random.choice(COPY_LINES)}</i>"
    )
    try:
        res = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            data={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            },
            timeout=10
        )
        return res.ok
    except Exception as e:
        print(f"❌ Telegram send failed: {e}")
        return False

def send_email(title, url):
    if not (EMAIL_ADDRESS and EMAIL_PASSWORD and EMAIL_RECIPIENT):
        print("✉️ Email config not set. Skipping.")
        return False
    try:
        recipients = [addr.strip() for addr in EMAIL_RECIPIENT.split(",") if addr.strip()]
        success = False

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            for recipient in recipients:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = title
                msg["From"] = EMAIL_ADDRESS
                msg["To"] = recipient

                text = f"{title}\n\nWatch here: {url}"
                html = f"""\
                <html>
                    <body>
                        <h3>{title}</h3>
                        <p><a href="{url}">▶ Watch Condensed Game</a></p>
                        <p><i>{random.choice(COPY_LINES)}</i></p>
                    </body>
                </html>
                """

                msg.attach(MIMEText(text, "plain"))
                msg.attach(MIMEText(html, "html"))
                server.sendmail(EMAIL_ADDRESS, recipient, msg.as_string())
                print(f"✅ Email sent to {recipient}")
                success = True

        return success
    except Exception as e:
        print(f"❌ Email failed: {e}")
        return False


def main():
    print("🎬 Condensed Game Bot (GitHub Actions version)")
    if FORCE_POST:
        print("⚡ FORCE_POST mode enabled — skipping already-posted check")
    gamepks = get_recent_gamepks(team_id=TEAM_ID)
    print(f"🧾 Found {len(gamepks)} recent Giants games")

    posted = False
    for gamepk in gamepks:
        print(f"🎬 Checking gamePk: {gamepk}")
        if not FORCE_POST and already_posted(gamepk):
            print("⏩ Already posted")
            continue

        title, url = find_condensed_game(gamepk)
        if url:
            telegram_success = send_telegram_message(title, url)
            email_success = send_email(title, url)
            if telegram_success or email_success:
                mark_as_posted(gamepk)
                print("✅ Posted to Telegram and/or emailed")
                posted = True
            else:
                print("⚠️ Message failed to send anywhere")
            break
        else:
            print(f"❌ No condensed game found for {gamepk}")

    if not posted and gamepks:
        now_uk = datetime.now(ZoneInfo("Europe/London"))
        if now_uk.hour >= NO_GAME_CUTOFF_HOUR:
            print(f"⏰ Past {NO_GAME_CUTOFF_HOUR}:00 UK time with no game posted — sending alert")
            alert = "⚠️ Breakfast bot: past cutoff time and no condensed game found. Check MLB highlights manually."
            try:
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                    data={"chat_id": TELEGRAM_CHAT_ID, "text": alert},
                    timeout=10
                )
            except Exception as e:
                print(f"❌ Alert send failed: {e}")

if __name__ == "__main__":
    main()
