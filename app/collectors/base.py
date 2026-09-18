from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from pydantic import BaseModel

from app.config import Secrets, UserSettings


class JobPostingData(BaseModel):
    source: str
    external_id: str
    title: str
    company: str = ""
    location: str = ""
    url: str
    description: str = ""
    posted_at: datetime


class Collector(ABC):
    """Every source implements fetch_recent() and returns normalized postings
    posted within the last `lookback_hours` (default 24).

    Collection only — never submits an application. That stays in app/apply/.
    """

    name: str

    @abstractmethod
    def fetch_recent(
        self, settings: UserSettings, secrets: Secrets, lookback_hours: int = 24
    ) -> list[JobPostingData]:
        raise NotImplementedError
