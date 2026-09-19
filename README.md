# WebWork Due-Date Notifier (TTU)

Reminds you by email when a WebWork homework set is due soon, even though
TTU's WebWork sits behind eRaider SSO + Duo.

## Important limitation, read first

Duo can't be fully automated by a script — there's no way for unattended
code to tap "Approve" on your phone. This project works around that by
capturing an already-authenticated browser session once (`capture_session.py`,
run manually by you) and having the scheduled job reuse that session. When
the session eventually expires, you'll get an email telling you to refresh
it — a 2-minute manual step, not a full rebuild.

**`storage_state.json` contains live session cookies for your TTU account.
Never put it in a public repo. Keep this repo private.**

## Setup

1. **Install dependencies locally:**
   ```
   pip install -r requirements.txt
   playwright install chromium
   ```

2. **Set your course URL** in `config.json` (`webwork_course_url`), and
   adjust `reminder_days_before` if you want different thresholds than
   "3 days out and 1 day out".

3. **Capture your session** (do this on your own computer, not a server):
   ```
   python capture_session.py
   ```
   A browser window opens. Log in through eRaider, approve the Duo push,
   check "remember this browser" if offered, then press Enter in the
   terminal once you're on your course page. This creates
   `storage_state.json`.

4. **Inspect the real WebWork page structure.** The scraper in
   `scrape_and_notify.py` (`parse_assignments`) is a generic starting point —
   it looks for table rows containing a date-like string. Open your
   "Homework Sets" page in a browser, right-click a due-date cell → Inspect,
   and adjust the selectors so it reliably grabs the assignment name and
   due date. This is the one part that needs your eyes on the actual page.

5. **Set up a Gmail app password** for sending mail:
   Google Account → Security → 2-Step Verification → App passwords.
   (Don't use your real Gmail password.)

6. **Create a private GitHub repo** and push these files.

7. **Add these as GitHub repo secrets** (Settings → Secrets and variables →
   Actions):
   - `STORAGE_STATE` — paste the entire contents of `storage_state.json`
   - `EMAIL_FROM` — your Gmail address
   - `EMAIL_APP_PASSWORD` — the app password from step 5
   - `EMAIL_TO` — where you want reminders sent (can be the same address)
   - `ERAIDER_USERNAME` / `ERAIDER_PASSWORD` — stored for completeness;
     currently unused by the script directly since Duo blocks fresh logins
     anyway, but keep them out of code either way

8. **Test manually** from the Actions tab (`Run workflow` button) before
   trusting the daily schedule.

## When it stops working

If you get a "session expired" email, run `capture_session.py` again
locally, then update the `STORAGE_STATE` secret with the new file contents.

## Files

| File | Purpose |
|---|---|
| `config.json` | Course URL, reminder day thresholds |
| `capture_session.py` | Run once locally to log in and save a session |
| `scrape_and_notify.py` | The scheduled job: scrape + compare + email |
| `state.json` | Auto-generated; tracks which reminders were already sent |
| `.github/workflows/check.yml` | Daily GitHub Actions schedule |
