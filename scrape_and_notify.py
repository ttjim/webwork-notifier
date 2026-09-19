"""
Scheduled entry point. Run via GitHub Actions (see .github/workflows/check.yml)
or manually with `python scrape_and_notify.py`.

Env vars required (set as GitHub secrets in production):
    EMAIL_FROM        - Gmail address to send from
    EMAIL_APP_PASSWORD - Gmail app password (not your real password)
    EMAIL_TO          - where reminders should be sent (can be same as EMAIL_FROM)
    ERAIDER_USERNAME  - only used as a fallback if the saved session is dead;
                         will NOT get you past a fresh Duo prompt on its own
    ERAIDER_PASSWORD  - see above

Files used:
    config.json         - course URL + reminder thresholds (see config_loader.py)
    storage_state.json  - saved authenticated session from capture_session.py
    state.json          - tracks which reminders were already sent (auto-created)
"""

import json
import os
import re
import smtplib
import sys
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path

from bs4 import BeautifulSoup
from dateutil import parser as dateparser
from playwright.sync_api import sync_playwright

import config_loader

BASE_DIR = Path(__file__).parent
STORAGE_STATE_PATH = BASE_DIR / "storage_state.json"
STATE_PATH = BASE_DIR / "state.json"

CONFIG = config_loader.load()


def load_state():
    if STATE_PATH.exists():
        with open(STATE_PATH) as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2, default=str)


def send_email(subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = os.environ["EMAIL_FROM"]
    msg["To"] = os.environ["EMAIL_TO"]

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(os.environ["EMAIL_FROM"], os.environ["EMAIL_APP_PASSWORD"])
        server.send_message(msg)


def fetch_course_page_html():
    """Loads the saved session, navigates to the course page, returns HTML.

    Returns None if the session looks dead (redirected to a login/Duo page).
    """
    if not STORAGE_STATE_PATH.exists():
        raise RuntimeError(
            "storage_state.json not found. Run capture_session.py locally first."
        )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=str(STORAGE_STATE_PATH))
        page = context.new_page()
        page.goto(CONFIG["webwork_course_url"], wait_until="networkidle")

        current_url = page.url.lower()
        # TODO: adjust these substrings if TTU's login/Duo URLs differ
        if any(kw in current_url for kw in ("eraider", "cas", "duosecurity", "login")):
            browser.close()
            return None

        html = page.content()

        # Refresh storage state in case cookies were rotated
        context.storage_state(path=str(STORAGE_STATE_PATH))
        browser.close()
        return html


def parse_assignments(html):
    """Parse assignment name -> due datetime from the WebWork homework sets page.

    Matches TTU's current WebWork theme: each assignment is a
    <li class="list-group-item" data-set-status="..." ...> containing a
    <div dir="ltr"> with the set name/link, and a <div class="font-sm"> with
    text like "Open. Due September 18, 2026, 11:59:00 PM CDT."
    """
    soup = BeautifulSoup(html, "html.parser")
    assignments = {}

    due_pattern = re.compile(r"Due\s+(.+)", re.IGNORECASE)

    for li in soup.select("li.list-group-item"):
        name_el = li.select_one('div[dir="ltr"]')
        due_el = li.select_one("div.font-sm")
        if not name_el or not due_el:
            continue

        name = name_el.get_text(strip=True)
        due_text = due_el.get_text(strip=True)
        if not name or not due_text:
            continue

        match = due_pattern.search(due_text)
        if not match:
            # e.g. sets with no due text ("Closed", "Answers available", etc.)
            continue

        date_str = match.group(1).rstrip(".").strip()
        try:
            due = dateparser.parse(date_str, fuzzy=True)
        except (ValueError, OverflowError):
            continue
        # Drop timezone info (e.g. from "CDT") so it compares cleanly
        # against the naive local `now` used in check_and_notify().
        due = due.replace(tzinfo=None)

        assignments[name] = due

    return assignments


def check_and_notify():
    html = fetch_course_page_html()
    if html is None:
        send_email(
            "WebWork notifier: session expired",
            "The saved WebWork session looks expired or Duo is blocking login.\n"
            "Run capture_session.py on your computer to log in again and "
            "refresh storage_state.json, then update the STORAGE_STATE secret.",
        )
        sys.exit(1)

    assignments = parse_assignments(html)
    if not assignments:
        print("No assignments parsed — check parse_assignments() selectors.")
        return

    state = load_state()
    now = datetime.now()
    reminder_days = CONFIG["reminder_days_before"]

    for name, due in assignments.items():
        days_left = (due - now).days
        sent_thresholds = state.setdefault(name, [])

        for threshold in reminder_days:
            if days_left <= threshold and threshold not in sent_thresholds:
                send_email(
                    f"WebWork reminder: {name} due soon",
                    f"'{name}' is due {due.strftime('%A, %b %d at %I:%M %p')}.\n"
                    f"That's {days_left} day(s) away.",
                )
                sent_thresholds.append(threshold)
                print(f"Sent reminder for {name} (threshold {threshold})")

    save_state(state)


if __name__ == "__main__":
    check_and_notify()
