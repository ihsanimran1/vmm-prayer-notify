"""
VMM Prayer Time Notifications
Runs once, finds the next upcoming prayer, waits for it, sends one notification.
GitHub Actions triggers this every hour to check and fire the next prayer.
Pass --test to send a test notification immediately (for manual runs).
"""

import requests
from datetime import datetime
import pytz
import time
import os
import sys

PUSHOVER_USER_KEY  = os.environ["PUSHOVER_USER_KEY"]
PUSHOVER_API_TOKEN = os.environ["PUSHOVER_API_TOKEN"]

CITY     = "Melbourne"
COUNTRY  = "Australia"
METHOD   = 3  # Muslim World League — same as VMM
TIMEZONE = "Australia/Melbourne"

PRAYERS = ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]
SUMMARY_PRAYERS = ["Fajr", "Sunrise", "Dhuhr", "Asr", "Maghrib", "Isha", "Sunset"]

def fetch_prayer_times():
    tz = pytz.timezone(TIMEZONE)
    today = datetime.now(tz).strftime("%d-%m-%Y")
    url = f"https://api.aladhan.com/v1/timingsByCity/{today}?city={CITY}&country={COUNTRY}&method={METHOD}"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    return data["data"]["timings"]

def parse_time(time_str):
    tz = pytz.timezone(TIMEZONE)
    today = datetime.now(tz).date()
    naive = datetime.strptime(f"{today} {time_str[:5]}", "%Y-%m-%d %H:%M")
    return tz.localize(naive)

def send_notification(title, message):
    payload = {
        "token":    PUSHOVER_API_TOKEN,
        "user":     PUSHOVER_USER_KEY,
        "title":    title,
        "message":  message,
        "priority": 0,
    }
    resp = requests.post("https://api.pushover.net/1/messages.json", data=payload, timeout=10)
    resp.raise_for_status()
    print(f"Notification sent: {title}")

def main():
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    timings = fetch_prayer_times()

    # --summary flag: send today's full daily summary
    if "--summary" in sys.argv or "--test" in sys.argv:
        title = "Today's prayer times" if "--summary" in sys.argv else "VMM setup is working!"
        message = "\n".join(f"{p}: {timings[p][:5]}" for p in SUMMARY_PRAYERS)
        send_notification(title, message)
        return

    # Normal run: find the next prayer within the next hour
    for prayer in PRAYERS:
        prayer_dt = parse_time(timings[prayer])
        diff = (prayer_dt - now).total_seconds()

        if 0 < diff <= 5400:
            print(f"{prayer} is in {int(diff)}s — waiting...")
            time.sleep(diff)
            send_notification(
                f"{prayer} — time to pray",
                f"It is now {prayer_dt.strftime('%I:%M %p')}"
            )
            return

    print("No prayer in the next hour — nothing to do.")

if __name__ == "__main__":
    main()
