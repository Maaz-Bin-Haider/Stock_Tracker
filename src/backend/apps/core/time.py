"""Business-time helpers (FR-128, TECHNICAL_ARCHITECTURE §9.3).

Timestamps are stored in UTC; every "today" boundary (dashboard cards, default
date-filter ranges, daily report grouping, past-cutoff snapshots) is computed in
the business time zone via these helpers — never with ad-hoc ``date.today()``.
"""

import datetime
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import timezone


def business_tz() -> ZoneInfo:
    return ZoneInfo(settings.BUSINESS_TZ)


def business_today() -> datetime.date:
    return timezone.now().astimezone(business_tz()).date()


def business_day_bounds(day: datetime.date) -> tuple[datetime.datetime, datetime.datetime]:
    """UTC datetimes for [start, end) of the given calendar day in business time."""
    tz = business_tz()
    start = datetime.datetime.combine(day, datetime.time.min, tzinfo=tz)
    end = start + datetime.timedelta(days=1)
    return start.astimezone(datetime.UTC), end.astimezone(datetime.UTC)
