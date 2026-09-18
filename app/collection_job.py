from __future__ import annotations

import logging

from app.collectors.registry import ALL_COLLECTORS
from app.config import get_secrets, load_settings
from app.db import JobPosting, get_session, init_db
from app.filters import within_experience
from app.notify import send_daily_summary

logger = logging.getLogger(__name__)


def run_collection(lookback_hours: int = 24) -> int:
    """Fetch postings from the last `lookback_hours` from every enabled source
    and upsert them into SQLite, deduped by (source, external_id). Returns the
    count of newly inserted postings.
    """
    init_db()
    settings = load_settings()
    secrets = get_secrets()

    new_count = 0
    with get_session() as session:
        for source_name in settings.sources_enabled:
            collector = ALL_COLLECTORS.get(source_name)
            if collector is None:
                logger.warning("Unknown collector %s in sources_enabled, skipping", source_name)
                continue
            try:
                postings = collector.fetch_recent(settings, secrets, lookback_hours)
            except Exception:
                logger.exception("Collector %s failed", source_name)
                continue

            for posting in postings:
                if not within_experience(
                    posting, settings.min_years_experience, settings.max_years_experience
                ):
                    continue
                exists = (
                    session.query(JobPosting)
                    .filter_by(source=posting.source, external_id=posting.external_id)
                    .first()
                )
                if exists is not None:
                    continue
                session.add(
                    JobPosting(
                        source=posting.source,
                        external_id=posting.external_id,
                        title=posting.title,
                        company=posting.company,
                        location=posting.location,
                        url=posting.url,
                        description=posting.description,
                        posted_at=posting.posted_at,
                        status="pending",
                    )
                )
                new_count += 1
        session.commit()

    if new_count > 0:
        send_daily_summary(new_count, secrets)
    return new_count
