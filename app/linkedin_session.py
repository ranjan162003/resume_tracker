"""Shared LinkedIn browser session, reused by the collector and the apply
automation so both benefit from the same persisted login (data/storage_state.json)
instead of logging in every run — fewer logins looks less bot-like and is faster.

Login is manual, not credential-based: no LinkedIn password is ever stored on
disk. The first time (or whenever the saved session expires), a visible browser
window opens on LinkedIn's real login page and waits for you to log in yourself;
only the resulting session cookies get saved.
"""
from __future__ import annotations

from playwright.sync_api import BrowserContext, Playwright, sync_playwright

from app.config import STORAGE_STATE_PATH

LOGIN_URL = "https://www.linkedin.com/login"
MANUAL_LOGIN_TIMEOUT_MS = 300_000  # 5 minutes to log in (and clear 2FA if prompted)


def ensure_login() -> None:
    """Used by the dashboard's "Login to LinkedIn" button: opens a visible
    browser for manual login if the saved session is missing or expired, then
    saves it and closes. No-op (returns almost immediately) if already logged in.
    """
    with sync_playwright() as p:
        context = get_logged_in_context(p, headless=False)
        context.storage_state(path=str(STORAGE_STATE_PATH))
        context.close()


def get_logged_in_context(playwright: Playwright, headless: bool = True) -> BrowserContext:
    if STORAGE_STATE_PATH.exists():
        browser = playwright.chromium.launch(headless=headless)
        context = browser.new_context(storage_state=str(STORAGE_STATE_PATH))
        if _session_is_valid(context):
            return context
        context.close()
        browser.close()

    # No valid saved session -- open a visible browser so you can log in yourself.
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    _wait_for_manual_login(context)
    context.storage_state(path=str(STORAGE_STATE_PATH))
    return context


def _session_is_valid(context: BrowserContext) -> bool:
    page = context.new_page()
    page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
    is_valid = "login" not in page.url
    page.close()
    return is_valid


def _wait_for_manual_login(context: BrowserContext) -> None:
    page = context.new_page()
    page.goto(LOGIN_URL, wait_until="domcontentloaded")
    page.wait_for_url(
        lambda url: "linkedin.com/login" not in url and "checkpoint" not in url,
        timeout=MANUAL_LOGIN_TIMEOUT_MS,
    )
    page.close()
