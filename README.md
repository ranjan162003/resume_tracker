# resume_tracker

Collects job postings from the last 24 hours (LinkedIn + free job-board APIs) into
one Streamlit dashboard, with the title, company, location, and a direct link to
each posting. Nothing is ever auto-submitted anywhere — every source redirects to
a page with its own layout that can't be reliably auto-filled, so "Apply" just
opens the link for you and marks it as opened.

The "last 24 hours" window is computed fresh every time collection runs, not tied to
a fixed schedule — so the way to use this is just opening the dashboard and clicking
**"Run collection now"** whenever you're at your laptop. No background process or
scheduled task is required for that to work correctly.

**Note:** scraping LinkedIn's search results goes against their Terms of Service and
risks your account being flagged. This tool never submits anything on your behalf,
but the collection itself still carries that risk, which is yours to accept.

## Setup

```
python -m venv .venv
./.venv/Scripts/activate        # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
cp .env.example .env            # fill in any API keys you have
```

Free API keys (optional, only needed for the sources you enable):
- Adzuna: https://developer.adzuna.com/
- Jooble: https://jooble.org/api/about
- RemoteOK needs no key.

**LinkedIn needs no key or password in `.env` at all.** The first time it's used (or
whenever the saved session expires), use the **"Login to LinkedIn"** button on the
Settings page — a visible browser window opens on LinkedIn's own login page and waits
for you to log in yourself. Only the resulting session is saved to
`data/storage_state.json` (gitignored) — your password is never written to disk.
(If your LinkedIn account only uses "Sign in with Google," add a direct LinkedIn
password first under LinkedIn's own Settings → Sign in & security — Google blocks
its sign-in flow from automated browsers.)

## Run

Start the dashboard:
```
python run_dashboard.py
```
Open http://localhost:8501, go to **Settings** first to set your keywords, location,
and enabled sources, then use **"Run collection now"** in the sidebar whenever you
want to pull in the last 24 hours (or 48h/72h/7 days, adjustable in the sidebar) of
postings. There's no background process to keep running -- the lookback window is
computed fresh at whatever moment you click the button.

## Tests
```
pytest
```
