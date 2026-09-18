"""On-demand full job-description fetch for sources whose list view doesn't
expose one (LinkedIn, WorkAtAStartup). Only ever called for the single job
the user clicked "Tailor resume" on -- not a bulk scrape. The caller
(app.resume_agent.pipeline) is responsible for caching the result back onto
JobPosting.description so it's never re-fetched.

Neither site's description sits behind a stable CSS class (LinkedIn's in
particular is dynamically generated), so this reads the full rendered page
text and slices out the section between two reliable landmark strings
instead of targeting a specific element.
"""
from __future__ import annotations

from playwright.sync_api import sync_playwright

from app.linkedin_session import get_logged_in_context


def fetch_linkedin_description(url: str) -> str:
    with sync_playwright() as p:
        context = get_logged_in_context(p)
        page = context.new_page()
        page.goto(url, wait_until="networkidle")
        page.wait_for_timeout(1500)
        body_text = page.locator("body").inner_text()
        context.close()
    return _between(body_text, "About the job", "Set alert for similar jobs") or body_text


def fetch_workatastartup_description(url: str) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")
        page.wait_for_timeout(1000)
        body_text = page.locator("body").inner_text()
        browser.close()
    # The description sits between the first and second "Apply now" buttons
    # (top of the page, and again after "Other jobs at <company>").
    return _between(body_text, "Apply now", "Apply now") or body_text


def _between(text: str, start_marker: str, end_marker: str) -> str:
    start = text.find(start_marker)
    if start == -1:
        return ""
    start += len(start_marker)
    end = text.find(end_marker, start)
    if end == -1:
        return text[start:].strip()
    return text[start:end].strip()
