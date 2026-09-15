from datetime import datetime, timedelta, timezone

import httpx

from app.collectors.adzuna import AdzunaCollector
from app.collectors.jooble import JoobleCollector
from app.collectors.remoteok import RemoteOKCollector
from app.collectors.weworkremotely import WeWorkRemotelyCollector
from app.config import Secrets, UserSettings


class FakeResponse:
    def __init__(self, json_data=None, text_data=None):
        self._json = json_data
        self.text = text_data

    def raise_for_status(self):
        pass

    def json(self):
        return self._json


def test_adzuna_normalizes_results(monkeypatch):
    now = datetime.now(timezone.utc)
    fake_json = {
        "results": [
            {
                "id": 123,
                "title": "Python Developer",
                "company": {"display_name": "Acme"},
                "location": {"display_name": "Remote"},
                "redirect_url": "https://example.com/job/123",
                "description": "desc",
                "created": now.isoformat().replace("+00:00", "Z"),
            }
        ]
    }
    monkeypatch.setattr(httpx, "get", lambda *a, **k: FakeResponse(fake_json))

    settings = UserSettings(keywords=["python"], location="India")
    secrets = Secrets(adzuna_app_id="id", adzuna_app_key="key")

    postings = AdzunaCollector().fetch_recent(settings, secrets)
    assert len(postings) == 1
    assert postings[0].source == "adzuna"
    assert postings[0].external_id == "123"
    assert postings[0].title == "Python Developer"


def test_adzuna_skips_when_no_credentials():
    settings = UserSettings(keywords=["python"])
    secrets = Secrets()
    assert AdzunaCollector().fetch_recent(settings, secrets) == []


def test_jooble_normalizes_results(monkeypatch):
    # Jooble's `updated` field isn't a reliable "posted recently" signal (confirmed
    # against the live API), so unlike the other collectors this doesn't filter by
    # age -- it just normalizes whatever the API returns.
    now = datetime.now(timezone.utc)
    fake_json = {
        "jobs": [
            {
                "id": 1,
                "title": "Python Job",
                "company": "Acme",
                "location": "Remote",
                "link": "https://x/1",
                "snippet": "s",
                "updated": now.replace(tzinfo=None).isoformat(),
            },
        ]
    }
    captured_requests = []
    monkeypatch.setattr(
        httpx,
        "post",
        lambda url, json=None, **k: captured_requests.append(json) or FakeResponse(fake_json),
    )

    settings = UserSettings(keywords=["python"], location="Chennai", country_code="in")
    secrets = Secrets(jooble_api_key="key")

    postings = JoobleCollector().fetch_recent(settings, secrets)
    assert len(postings) == 1
    assert postings[0].title == "Python Job"
    # location should have the country appended, since bare city names return
    # zero results from Jooble's real API
    assert captured_requests[0]["location"] == "Chennai, India"


def test_remoteok_filters_by_keyword_and_recency(monkeypatch):
    now = datetime.now(timezone.utc)
    old = now - timedelta(days=3)
    fake_json = [
        {"legal": "notice"},
        {
            "id": "1",
            "date": now.isoformat(),
            "position": "Python Engineer",
            "tags": ["python", "backend"],
            "company": "Acme",
            "url": "https://remoteok.com/1",
            "description": "desc",
        },
        {
            "id": "2",
            "date": old.isoformat(),
            "position": "Python Engineer",
            "tags": ["python"],
            "company": "Old Co",
            "url": "https://remoteok.com/2",
            "description": "desc",
        },
        {
            "id": "3",
            "date": now.isoformat(),
            "position": "Java Engineer",
            "tags": ["java"],
            "company": "OtherCo",
            "url": "https://remoteok.com/3",
            "description": "desc",
        },
    ]
    monkeypatch.setattr(httpx, "get", lambda *a, **k: FakeResponse(fake_json))

    settings = UserSettings(keywords=["python"])
    secrets = Secrets()

    postings = RemoteOKCollector().fetch_recent(settings, secrets)
    assert len(postings) == 1
    assert postings[0].external_id == "1"


def test_weworkremotely_parses_rss_and_filters(monkeypatch):
    now = datetime.now(timezone.utc)
    old = now - timedelta(days=3)

    def rfc2822(dt: datetime) -> str:
        return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0"><channel>
      <item>
        <title>Acme: Python Developer</title>
        <link>https://weworkremotely.com/remote-jobs/acme-python-developer</link>
        <region>Anywhere in the World</region>
        <pubDate>{rfc2822(now)}</pubDate>
      </item>
      <item>
        <title>OldCo: Python Developer</title>
        <link>https://weworkremotely.com/remote-jobs/oldco-python-developer</link>
        <region>Anywhere in the World</region>
        <pubDate>{rfc2822(old)}</pubDate>
      </item>
      <item>
        <title>Acme: Java Developer</title>
        <link>https://weworkremotely.com/remote-jobs/acme-java-developer</link>
        <region>Anywhere in the World</region>
        <pubDate>{rfc2822(now)}</pubDate>
      </item>
    </channel></rss>"""
    monkeypatch.setattr(httpx, "get", lambda *a, **k: FakeResponse(text_data=rss))

    settings = UserSettings(keywords=["python"])
    secrets = Secrets()

    postings = WeWorkRemotelyCollector().fetch_recent(settings, secrets)
    assert len(postings) == 1
    assert postings[0].company == "Acme"
    assert postings[0].title == "Python Developer"
