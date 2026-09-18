"""One-time (or whenever the session expires) manual LinkedIn login.

Run this yourself from your own terminal: `python login_linkedin.py`
A Chrome window opens on LinkedIn's real login page -- log in there normally
(password, 2FA, whatever LinkedIn asks). Once you land on your feed, this
script saves the session to data/storage_state.json and exits. After that,
the collector and Easy Apply automation reuse this session without asking
you to log in again, until it expires.

Note: run this directly yourself, not through an automated tool -- the
browser needs to be part of your own interactive desktop session to receive
your keyboard/mouse input.
"""
from app.config import STORAGE_STATE_PATH
from app.linkedin_session import ensure_login

if __name__ == "__main__":
    print("Log in to LinkedIn in the window that opens. Waiting up to 5 minutes...")
    ensure_login()
    print(f"Saved session to {STORAGE_STATE_PATH}")
