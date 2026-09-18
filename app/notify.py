from __future__ import annotations

import logging
import smtplib
from email.mime.text import MIMEText

from app.config import Secrets

logger = logging.getLogger(__name__)


def send_daily_summary(new_count: int, secrets: Secrets) -> None:
    if not secrets.notify_enabled or not secrets.smtp_host or not secrets.notify_email_to:
        return

    message = MIMEText(f"Resume Tracker collected {new_count} new job posting(s) today. Review them in the dashboard.")
    message["Subject"] = "Resume Tracker: new jobs today"
    message["From"] = secrets.smtp_user
    message["To"] = secrets.notify_email_to

    try:
        with smtplib.SMTP(secrets.smtp_host, secrets.smtp_port) as server:
            server.starttls()
            if secrets.smtp_user:
                server.login(secrets.smtp_user, secrets.smtp_password)
            server.send_message(message)
    except Exception:
        logger.exception("Failed to send daily summary email")
