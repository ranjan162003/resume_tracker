"""We Work Remotely collection via their official public RSS feed -- no
scraping, no API key, no ToS concerns. Titles are formatted "Company: Role",
which we split back apart.

Uses the all-categories feed rather than a per-category one (e.g.
remote-programming-jobs.rss) -- category feeds were found to be stale (not
updating for weeks), while the all-jobs feed updates live. Keyword filtering
happens client-side instead, same approach as the RemoteOK collector.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import httpx

from app.config import Secrets, UserSettings
from app.collectors.base import Collector, JobPostingData

RSS_URL = "https://weworkremotely.com/remote-jobs.rss"


class WeWorkRemotelyCollector(Collector):
    name = "weworkremotely"

    def fetch_recent(
        self, settings: UserSettings, secrets: Secrets, lookback_hours: int = 24
    ) -> list[JobPostingData]:
        resp = httpx.get(RSS_URL, headers={"User-Agent": "resume-tracker/1.0"}, timeout=30)
        resp.raise_for_status()

        cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
        keywords = [k.lower() for k in settings.keywords]

        root = ET.fromstring(resp.text)
        postings: list[JobPostingData] = []
        for item in root.findall(".//item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            region = (item.findtext("region") or "").strip()
            if not title or not link:
                continue

            posted_at = _parse_pub_date(item.findtext("pubDate") or "")
            if posted_at is None or posted_at < cutoff:
                continue

            if keywords and not any(k in title.lower() for k in keywords):
                continue

            company, sep, role = title.partition(":")
            company = company.strip()
            job_title = role.strip() if sep else title
            description = _strip_html(item.findtext("description") or "")

            postings.append(
                JobPostingData(
                    source=self.name,
                    external_id=link,
                    title=job_title,
                    company=company,
                    location=region or "Remote",
                    url=link,
                    description=description,
                    posted_at=posted_at,
                )
            )
        return postings


def _strip_html(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html).strip()


def _parse_pub_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed
