"""The single, hardcoded application-wide timezone this feature computes 'today'/'now' against.

Per RES-02: no per-organization/per-dojo timezone concept exists or is added.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

APP_TIMEZONE = ZoneInfo("America/Sao_Paulo")


def local_now() -> datetime:
    """Current timezone-aware instant, expressed in the application's fixed timezone."""
    return datetime.now(APP_TIMEZONE)


def local_today() -> date:
    """Current wall-clock calendar date in the application's fixed timezone.

    This is the one place a UTC-vs-local distinction is actually load-bearing
    (see plan.md Autocritica) -- every "today"/day-of-week computation in
    EventSeriesService goes through this function, not a bare datetime.now(UTC).
    """
    return local_now().date()
