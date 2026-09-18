from __future__ import annotations

from datetime import datetime, timezone

import httpx

from app.config import Secrets, UserSettings
from app.collectors.base import Collector, JobPostingData

# Jooble's location matching needs "City, Country" -- a bare city name (even a
# correctly spelled one) reliably returns zero results, confirmed by testing
# "Chennai" (0 results) vs "Chennai, India" (141 results) against the live API.
#
# Its `updated` field also isn't a reliable "posted recently" signal -- live
# testing showed values weeks old even for currently-listed results. So unlike
# Adzuna/RemoteOK/WWR, this doesn't filter by `lookback_hours` at all; like
# WorkAtAStartup, it relies on (source, external_id) dedup so only genuinely
# new postings show up as pending on repeat runs.
COUNTRY_NAMES = {
    "in": "India",
    "us": "United States",
    "gb": "United Kingdom",
    "ca": "Canada",
    "au": "Australia",
    "de": "Germany",
    "fr": "France",
    "sg": "Singapore",
}


class JoobleCollector(Collector):
    name = "jooble"

    def fetch_recent(
        self, settings: UserSettings, secrets: Secrets, lookback_hours: int = 24
    ) -> list[JobPostingData]:
        if not secrets.jooble_api_key:
            return []

        country = COUNTRY_NAMES.get(settings.country_code.lower(), settings.country_code)
        cities = [loc.strip() for loc in settings.location.split(",") if loc.strip()]
        locations = [f"{city}, {country}" for city in cities] or [""]

        postings: list[JobPostingData] = []
        for keyword in settings.keywords:
            for location in locations:
                resp = httpx.post(
                    f"https://jooble.org/api/{secrets.jooble_api_key}",
                    json={"keywords": keyword, "location": location},
                    timeout=30,
                )
                resp.raise_for_status()
                for job in resp.json().get("jobs", []):
                    posted_at = _parse_updated(job.get("updated", "")) or datetime.now(timezone.utc)
                    postings.append(
                        JobPostingData(
                            source=self.name,
                            external_id=str(job.get("id", job.get("link", ""))),
                            title=job.get("title", ""),
                            company=job.get("company", ""),
                            location=job.get("location", ""),
                            url=job.get("link", ""),
                            description=job.get("snippet", ""),
                            posted_at=posted_at,
                        )
                    )
        return postings


def _parse_updated(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)
    except ValueError:
        return None
