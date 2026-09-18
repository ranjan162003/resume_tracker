"""Y Combinator's job board (workatastartup.com) via Playwright. No login
needed to browse listings. The site exposes no recency filter or posted-at
timestamp, so this can't restrict to `lookback_hours` server-side like the
others -- it scrapes whatever's currently listed and relies on
(source, external_id) dedup so only genuinely new postings show up as
pending on repeat runs.

The list view also doesn't expose a job description (only title/company/
location/type/salary), so app/filters.py's years-of-experience filter has
only the title to match against here -- it will rarely exclude anything.
"""
from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright

from app.config import Secrets, UserSettings
from app.collectors.base import Collector, JobPostingData

JOBS_URL = "https://www.workatastartup.com/jobs"


class WorkAtAStartupCollector(Collector):
    name = "workatastartup"

    def fetch_recent(
        self, settings: UserSettings, secrets: Secrets, lookback_hours: int = 24
    ) -> list[JobPostingData]:
        keywords = [k.lower() for k in settings.keywords]
        postings: list[JobPostingData] = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(JOBS_URL, wait_until="domcontentloaded")
            page.wait_for_timeout(2500)

            links = page.locator("a[target='job']")
            for i in range(links.count()):
                posting = _parse_job_link(links.nth(i), keywords)
                if posting is not None:
                    postings.append(posting)
            browser.close()

        return postings


def _parse_job_link(link_el, keywords: list[str]) -> JobPostingData | None:
    href = link_el.get_attribute("href") or ""
    title = link_el.inner_text().strip()
    if not href or not title:
        return None
    if keywords and not any(k in title.lower() for k in keywords):
        return None

    card = link_el.locator("xpath=ancestor::div[contains(@class,'cursor-pointer')][1]")
    company_el = card.locator("a[target='company'] .font-bold").first
    company = company_el.inner_text().strip() if company_el.count() > 0 else ""

    detail_spans = card.locator(".job-details span")
    location = detail_spans.nth(1).inner_text().strip() if detail_spans.count() > 1 else ""

    external_id = href.rstrip("/").rsplit("/", 1)[-1]
    return JobPostingData(
        source="workatastartup",
        external_id=external_id,
        title=title,
        company=company,
        location=location,
        url=urljoin("https://www.workatastartup.com", href),
        posted_at=datetime.now(timezone.utc),
    )
