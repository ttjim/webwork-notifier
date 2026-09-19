"""
Run this ONCE, on your own computer, with a real browser window.

    python capture_session.py

It opens your WebWork course URL, walks you through eRaider + Duo login
yourself (you approve the Duo push on your phone like normal), and then
saves the authenticated session to storage_state.json.

The scheduled script (scrape_and_notify.py) reuses storage_state.json so
it never has to fight Duo on its own. When storage_state.json eventually
expires (Duo "remember this browser" runs out), just re-run this script
once to refresh it.

IMPORTANT: storage_state.json contains live session cookies for your TTU
account. Never commit it to a public repo. Treat it like a password.
"""

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

import config_loader

CONFIG = config_loader.load()
STORAGE_STATE_PATH = Path(__file__).parent / "storage_state.json"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        print(f"Opening {CONFIG['webwork_course_url']} ...")
        page.goto(CONFIG["webwork_course_url"])

        print()
        print("=" * 70)
        print("A browser window has opened.")
        print("Log in through eRaider and approve the Duo prompt as usual.")
        print("If Duo offers 'Remember me for N days', check that box.")
        print("Once you can see your WebWork homework sets page, come back")
        print("here and press Enter.")
        print("=" * 70)
        input("Press Enter once you're logged in and see your course page... ")

        context.storage_state(path=str(STORAGE_STATE_PATH))
        print(f"Saved session to {STORAGE_STATE_PATH}")
        print("Upload this file's contents as the STORAGE_STATE GitHub secret")
        print("(see README.md) and you're set until it expires.")

        browser.close()


if __name__ == "__main__":
    main()
