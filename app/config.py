"""Two kinds of configuration:
- Secrets: static, read from .env (credentials, API keys) — never edited via the UI.
- UserSettings: everyday preferences (search terms, filters, enabled sources) —
  edited via the Streamlit settings page and persisted to data/settings.json so
  they survive restarts.
"""
from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
SETTINGS_PATH = DATA_DIR / "settings.json"
DB_PATH = DATA_DIR / "resume_tracker.db"
STORAGE_STATE_PATH = DATA_DIR / "storage_state.json"
TAILORED_DIR = DATA_DIR / "tailored"
TAILORED_DIR.mkdir(exist_ok=True)
RESUME_DIR = DATA_DIR / "resume"
RESUME_DIR.mkdir(exist_ok=True)


class Secrets(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    adzuna_app_id: str = ""
    adzuna_app_key: str = ""
    jooble_api_key: str = ""

    notify_enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    notify_email_to: str = ""


class UserSettings(BaseModel):
    resume_path: str = ""  # local .docx path, used by the resume-tailoring agent
    keywords: list[str] = Field(default_factory=lambda: ["python developer"])
    location: str = ""
    country_code: str = "in"  # ISO country code, used by Adzuna/Jooble queries
    linkedin_experience_levels: list[str] = Field(default_factory=list)  # LinkedIn f_E codes; empty = any
    min_years_experience: int | None = None  # best-effort text match; None = no lower bound
    max_years_experience: int | None = None  # best-effort text match; None = no upper bound
    sources_enabled: list[str] = Field(
        default_factory=lambda: [
            "linkedin",
            "adzuna",
            "jooble",
            "remoteok",
            "weworkremotely",
            "workatastartup",
        ]
    )


def load_settings() -> UserSettings:
    if SETTINGS_PATH.exists():
        return UserSettings.model_validate(json.loads(SETTINGS_PATH.read_text()))
    return UserSettings()


def save_settings(settings: UserSettings) -> None:
    SETTINGS_PATH.write_text(settings.model_dump_json(indent=2))


def get_secrets() -> Secrets:
    return Secrets()
