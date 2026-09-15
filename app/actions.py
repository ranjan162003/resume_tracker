from __future__ import annotations

from datetime import datetime, timezone

from app.db import JobPosting, get_session


def confirm_apply(job_id: int) -> None:
    """Called only after the user clicks Apply (single or bulk) in the dashboard.

    No auto-submission anywhere: every source redirects to a page with its own
    layout that can't be reliably auto-filled, so this just marks the posting
    as opened -- the dashboard link is what you actually click to apply.
    """
    with get_session() as session:
        job = session.get(JobPosting, job_id)
        if job is None:
            return

        job.status = "opened"
        job.status_detail = "Opened for manual application."
        job.applied_at = datetime.now(timezone.utc)
        session.commit()
