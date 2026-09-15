"""LinkedIn collection via Playwright. Collection only — never submits anything.

Note: this scrapes LinkedIn's own search UI, which is against LinkedIn's Terms
of Service and their markup changes without notice, so selectors here may need
periodic updates. Kept deliberately simple/best-effort for that reason.

The f_TPR=r<seconds> URL parameter tells LinkedIn itself to only return
postings from the last N seconds, so that filtering happens server-side -- we
don't need to (and can't reliably) re-derive an exact posted-at timestamp from
the card markup, which doesn't expose one once logged in.

The search-results cards don't expose a job description (only title/company/
location), so app/filters.py's years-of-experience filter has only the title
to match against here -- it will rarely exclude anything for this source.
"""
from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import quote, urljoin

from playwright.sync_api import Locator, sync_playwright

from app.config import Secrets, UserSettings
from app.collectors.base import Collector, JobPostingData
from app.linkedin_session import get_logged_in_context

SEARCH_URL = (
    "https://www.linkedin.com/jobs/search/?keywords={keywords}&location={location}&f_TPR=r{seconds}"
)

# LinkedIn's own experience-level filter values (f_E), settable in Settings.
EXPERIENCE_LEVELS = {
    "1": "Internship",
    "2": "Entry level",
    "3": "Associate",
    "4": "Mid-Senior level",
    "5": "Director",
    "6": "Executive",
}


class LinkedInCollector(Collector):
    name = "linkedin"

    def fetch_recent(
        self, settings: UserSettings, secrets: Secrets, lookback_hours: int = 24
    ) -> list[JobPostingData]:
        postings: list[JobPostingData] = []
        locations = [loc.strip() for loc in settings.location.split(",") if loc.strip()] or [""]
        seconds = lookback_hours * 3600
        experience_suffix = (
            f"&f_E={','.join(settings.linkedin_experience_levels)}"
            if settings.linkedin_experience_levels
            else ""
        )

        with sync_playwright() as p:
            context = get_logged_in_context(p)
            page = context.new_page()
            for keyword in settings.keywords:
                for location in locations:
                    url = (
                        SEARCH_URL.format(
                            keywords=quote(keyword), location=quote(location), seconds=seconds
                        )
                        + experience_suffix
                    )
                    page.goto(url, wait_until="domcontentloaded")
                    page.wait_for_timeout(2000)  # let results render
                    cards = page.locator("div.job-card-container[data-job-id]")
                    for i in range(cards.count()):
                        posting = _parse_card(cards.nth(i))
                        if posting is not None:
                            postings.append(posting)
            context.close()

        return postings


def _parse_card(card: Locator) -> JobPostingData | None:
    external_id = card.get_attribute("data-job-id")
    if not external_id:
        return None

    link_el = card.locator("a.job-card-container__link").first
    title = (link_el.get_attribute("aria-label") or "").strip()
    href = link_el.get_attribute("href") or ""

    company_el = card.locator(".artdeco-entity-lockup__subtitle").first
    location_el = card.locator(".job-card-container__metadata-wrapper li").first

    return JobPostingData(
        source="linkedin",
        external_id=external_id,
        title=title,
        company=(company_el.inner_text().strip() if company_el.count() > 0 else ""),
        location=(location_el.inner_text().strip() if location_el.count() > 0 else ""),
        url=urljoin("https://www.linkedin.com", href),
        posted_at=datetime.now(timezone.utc),
    )
