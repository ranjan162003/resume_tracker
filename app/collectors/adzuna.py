from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

import httpx

from app.config import Secrets, UserSettings
from app.collectors.base import Collector, JobPostingData


class AdzunaCollector(Collector):
    name = "adzuna"

    def fetch_recent(
        self, settings: UserSettings, secrets: Secrets, lookback_hours: int = 24
    ) -> list[JobPostingData]:
        if not secrets.adzuna_app_id or not secrets.adzuna_app_key:
            return []

        cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
        max_days_old = max(1, math.ceil(lookback_hours / 24))  # Adzuna only accepts whole days
        locations = [loc.strip() for loc in settings.location.split(",") if loc.strip()] or [""]

        postings: list[JobPostingData] = []
        for keyword in settings.keywords:
            for location in locations:
                resp = httpx.get(
                    f"https://api.adzuna.com/v1/api/jobs/{settings.country_code}/search/1",
                    params={
                        "app_id": secrets.adzuna_app_id,
                        "app_key": secrets.adzuna_app_key,
                        "what": keyword,
                        "where": location,
                        "max_days_old": max_days_old,
                        "sort_by": "date",
                        "results_per_page": 50,
                    },
                    timeout=30,
                )
                resp.raise_for_status()
                for job in resp.json().get("results", []):
                    posted_at = datetime.fromisoformat(job["created"].replace("Z", "+00:00"))
                    if posted_at < cutoff:
                        continue
                    postings.append(
                        JobPostingData(
                            source=self.name,
                            external_id=str(job["id"]),
                            title=job.get("title", ""),
                            company=(job.get("company") or {}).get("display_name", ""),
                            location=(job.get("location") or {}).get("display_name", ""),
                            url=job.get("redirect_url", ""),
                            description=job.get("description", ""),
                            posted_at=posted_at,
                        )
                    )
        return postings
