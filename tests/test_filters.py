from datetime import datetime, timezone

from app.collectors.base import JobPostingData
from app.filters import extract_min_years, within_experience


def _posting(title: str, description: str = "") -> JobPostingData:
    return JobPostingData(
        source="test",
        external_id="1",
        title=title,
        url="https://example.com",
        description=description,
        posted_at=datetime.now(timezone.utc),
    )


def test_extract_min_years_finds_number():
    assert extract_min_years("Looking for 3+ years of experience") == 3


def test_extract_min_years_takes_smallest_when_multiple():
    assert extract_min_years("2 years for juniors, 5 years for seniors") == 2


def test_extract_min_years_none_when_absent():
    assert extract_min_years("No experience requirement mentioned") is None


def test_within_experience_no_filter_always_passes():
    posting = _posting("Senior Engineer", "10+ years required")
    assert within_experience(posting, None, None) is True


def test_within_experience_excludes_over_max():
    posting = _posting("Senior Engineer", "requires 8+ years experience")
    assert within_experience(posting, None, 3) is False


def test_within_experience_excludes_under_min():
    posting = _posting("Intern", "0 years experience needed")
    assert within_experience(posting, 2, 3) is False


def test_within_experience_includes_within_range():
    posting = _posting("Mid-level Engineer", "requires 2 years experience")
    assert within_experience(posting, 2, 3) is True


def test_within_experience_includes_when_unstated():
    posting = _posting("Software Engineer", "Join our growing team")
    assert within_experience(posting, 2, 3) is True
