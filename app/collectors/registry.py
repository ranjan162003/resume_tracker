from __future__ import annotations

from app.collectors.adzuna import AdzunaCollector
from app.collectors.base import Collector
from app.collectors.jooble import JoobleCollector
from app.collectors.linkedin import LinkedInCollector
from app.collectors.remoteok import RemoteOKCollector
from app.collectors.weworkremotely import WeWorkRemotelyCollector
from app.collectors.workatastartup import WorkAtAStartupCollector

ALL_COLLECTORS: dict[str, Collector] = {
    c.name: c
    for c in [
        LinkedInCollector(),
        AdzunaCollector(),
        JoobleCollector(),
        RemoteOKCollector(),
        WeWorkRemotelyCollector(),
        WorkAtAStartupCollector(),
    ]
}
