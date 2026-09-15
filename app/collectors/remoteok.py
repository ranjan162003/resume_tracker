from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx

from app.config import Secrets, UserSettings
from app.collectors.base import Collector, JobPostingData


class RemoteOKCollector(Collector):
    """No API key needed. RemoteOK returns one flat feed; we filter client-side
    by keyword and by the lookback cutoff since the API doesn't support max-age.
    """

    name = "remoteok"

    def fetch_recent(
        self, settings: UserSettings, secrets: Secrets, lookback_hours: int = 24
    ) -> list[JobPostingData]:
        resp = httpx.get(
            "https://remoteok.com/api",
            headers={"User-Agent": "resume-tracker/1.0"},
            timeout=30,
        )
        resp.raise_for_status()
        cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
        keywords = [k.lower() for k in settings.keywords]

        postings: list[JobPostingData] = []
        for job in resp.json():
            if "id" not in job or "date" not in job:
                continue  # first element is a legal notice, not a job
            try:
                posted_at = datetime.fromisoformat(job["date"]).astimezone(timezone.utc)
            except ValueError:
                continue
            if posted_at < cutoff:
                continue

            haystack = f"{job.get('position', '')} {' '.join(job.get('tags', []))}".lower()
            if keywords and not any(k in haystack for k in keywords):
                continue

            postings.append(
                JobPostingData(
                    source=self.name,
                    external_id=str(job["id"]),
                    title=job.get("position", ""),
                    company=job.get("company", ""),
                    location=job.get("location", "Remote"),
                    url=job.get("url", ""),
                    description=job.get("description", ""),
                    posted_at=posted_at,
                )
            )
        return postings
