"""Best-effort "years of experience" filtering, applied uniformly across all
sources after collection -- since none of them expose a structured years
field, this scans title+description text for patterns like "3 years" or
"3+ years" and compares the smallest number found to a user-set [min, max]
range, so a "2 to 3 years" filter excludes both entry-level and senior
postings, not just anything above the top end.

This is inherently approximate:
- Many postings don't state years at all -> treated as a pass (not excluded),
  since we'd rather show an unknown than hide a real match.
- Phrasing varies ("3-5 years" grabs the number touching "years", which for a
  range is the upper bound, not the lower one) -- good enough for a rough
  filter, not a precise one.
- LinkedIn and WorkAtAStartup don't expose a description in their list view
  (only title), so this filter has much less text to match against for those
  two sources and will rarely exclude anything there.
"""
from __future__ import annotations

import re

from app.collectors.base import JobPostingData

YEARS_PATTERN = re.compile(r"(\d{1,2})\+?\s*years?\b", re.IGNORECASE)


def extract_min_years(text: str) -> int | None:
    matches = YEARS_PATTERN.findall(text)
    if not matches:
        return None
    return min(int(m) for m in matches)


def within_experience(
    posting: JobPostingData, min_years: int | None, max_years: int | None
) -> bool:
    if min_years is None and max_years is None:
        return True
    required = extract_min_years(f"{posting.title} {posting.description}")
    if required is None:
        return True
    if min_years is not None and required < min_years:
        return False
    if max_years is not None and required > max_years:
        return False
    return True
