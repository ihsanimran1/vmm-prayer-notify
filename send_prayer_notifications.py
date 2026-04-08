"""
VMM Prayer Time Notifications
Fetches today's prayer times from Aladhan API (same calculation as awqat.com.au/vmm/)
and sends scheduled Pushover notifications to your iPhone.
"""

import requests
from datetime import datetime, timedelta
import pytz
import time
import sys
import os

# ── CONFIG ────────────────────────────────────────────────────────────────────
PUSHOVER_USER_KEY  = os.environ["PUSHOVER_USER_KEY"]   # your Pushover user key
PUSHOVER_API_TOKEN = os.environ["PUSHOVER_API_TOKEN"]  # your Pushover app token

CITY       = "Melbourne"
COUNTRY    = "Australia"
METHOD     = 3        # Muslim World League — same as VMM / awqat.com.au
TIMEZONE   = "Australia/Melbourne"

PRAYERS = ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]

PRAYER_EMOJI = {
    "Fajr":    "🌅",
    "Dhuhr":   "🌞",
    "Asr":     "🌤️",
    "Maghrib": "🌇",
    "Isha":    "🌙",
}
# ─────────────────────────────────────────────────────────────────────────────


def fetch_prayer_times() -> dict:
    """Fetch today's prayer times from Aladhan API."""
    tz = pytz.timezone(TIMEZONE)
    today = datetime.now(tz)
    date_str = today.strftime("%d-%m-%Y")

    url = (
        f"https://api.aladhan.com/v1/timingsByCity/{date_str}"
        f"?city={CITY}&country={COUNTRY}&method={METHOD}"
    )

    print(f"Fetching prayer times for {date_str} ({CITY})...")
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()

    data = resp.json()
    if data.get("code") != 200:
        raise ValueError(f"API error: {data}")

    timings = data["data"]["timings"]
    print("Prayer times fetched:")
    for p in PRAYERS:
        print(f"  {p}: {timings[p]}")

    return timings


def parse_prayer_time(time_str: str, tz) -> datetime:
    """Convert 'HH:MM' string to a timezone-aware datetime for today."""
    today = datetime.now(tz).date()
    naive = datetime.strptime(f"{today} {time_str[:5]}", "%Y-%m-%d %H:%M")
    return tz.localize(naive)


def send_pushover_notification(prayer: str, prayer_time: datetime, delay_seconds: int):
    """Send a Pushover notification scheduled at a Unix timestamp."""
    emoji = PRAYER_EMOJI.get(prayer, "🕌")
    title = f"{emoji} {prayer} — Time to Pray"
    message = f"{prayer} prayer time is now ({prayer_time.strftime('%I:%M %p')})"

    payload = {
        "token":     PUSHOVER_API_TOKEN,
        "user":      PUSHOVER_USER_KEY,
        "title":     title,
        "message":   message,
        "priority":  0,       # normal priority; use 1 for high-priority bypass DND
        "sound":     "none",  # silent — the adhan is in your heart 🙂
    }

    resp = requests.post(
        "https://api.pushover.net/1/messages.json",
        data=payload,
        timeout=10,
    )
    resp.raise_for_status()
    result = resp.json()

    if result.get("status") == 1:
        print(f"  ✅ Notification queued for {prayer} at {prayer_time.strftime('%H:%M')}")
    else:
        print(f"  ❌ Failed to queue {prayer}: {result}")


def main():
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)

    timings = fetch_prayer_times()

    print(f"\nScheduling notifications (current time: {now.strftime('%H:%M %Z')})...")

    scheduled = 0
    for prayer in PRAYERS:
        raw_time = timings[prayer]
        prayer_dt = parse_prayer_time(raw_time, tz)

        if prayer_dt <= now:
            print(f"  ⏩ Skipping {prayer} ({prayer_dt.strftime('%H:%M')}) — already passed")
            continue

        delay = int((prayer_dt - now).total_seconds())

        # Sleep until ~30s before the prayer time, then send the notification
        # (Pushover free tier doesn't support scheduled delivery, so we wait)
        # GitHub Actions keeps the runner alive for the whole job.
        print(f"  ⏳ Waiting {delay}s for {prayer} at {prayer_dt.strftime('%H:%M')}...")
        time.sleep(max(0, delay - 5))   # wake up 5s early

        send_pushover_notification(prayer, prayer_dt, delay)
        scheduled += 1

    if scheduled == 0:
        print("\nAll prayers have already passed for today. Nothing to notify.")
    else:
        print(f"\n✅ Done — sent {scheduled} notification(s).")


if __name__ == "__main__":
    main()
