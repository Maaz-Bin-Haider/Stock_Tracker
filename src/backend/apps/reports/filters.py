"""Shared report filter parsing (FR-097).

Query params arrive as strings; ``parse_filters`` normalizes them into typed
values once, so the JSON views and the export task (which replays the stored
params) interpret filters identically. Date-range filters on *timestamps* are
converted to UTC windows via the Dubai business-day helpers (FR-128);
date-range filters on user-entered DATE columns compare calendar dates.
"""

import datetime

from django.utils.dateparse import parse_date, parse_datetime
from rest_framework.exceptions import ValidationError

from apps.core.time import business_tz

# Every filter any report may declare; parse_filters accepts this vocabulary
# and ignores unknown params so stray query noise never breaks a report.
FILTER_KEYS = (
    "date_from",
    "date_to",
    "cutoff",
    "location",
    "product",
    "category",
    "supplier",
    "customer",
    "status",
    "bucket",
    "txn_type",
    "adjustment_type",
    "action",
    "module",
    "user",
    "search",
)

_DATE_KEYS = ("date_from", "date_to")
_INT_KEYS = ("location", "product", "category", "supplier", "customer", "user")


def _parse_cutoff(raw: str) -> datetime.datetime:
    """Cutoff is a Dubai-business-time datetime unless an offset is given."""
    value = parse_datetime(raw)
    if value is None:
        day = parse_date(raw)
        if day is None:
            raise ValidationError({"cutoff": f"Invalid datetime {raw!r}."})
        value = datetime.datetime.combine(day, datetime.time.max)
    if value.tzinfo is None:
        value = value.replace(tzinfo=business_tz())
    return value.astimezone(datetime.UTC)


def parse_filters(params) -> dict:
    filters = {}
    for key in FILTER_KEYS:
        raw = params.get(key)
        if raw in (None, ""):
            continue
        if key in _DATE_KEYS:
            value = parse_date(raw) if isinstance(raw, str) else raw
            if value is None:
                raise ValidationError({key: f"Invalid date {raw!r} (expected YYYY-MM-DD)."})
            filters[key] = value
        elif key == "cutoff":
            filters[key] = _parse_cutoff(raw) if isinstance(raw, str) else raw
        elif key in _INT_KEYS:
            try:
                filters[key] = int(raw)
            except (TypeError, ValueError) as exc:
                raise ValidationError({key: f"Invalid id {raw!r}."}) from exc
        else:
            filters[key] = str(raw).strip()
    return filters


def describe_filters(filters: dict) -> str:
    """Human-readable filter summary printed on export headers (FR-098:
    the file states exactly what was filtered)."""
    from apps.accounts.models import User
    from apps.masterdata.models import Category, Customer, Location, Supplier
    from apps.products.models import Product

    lookups = {
        "location": Location,
        "product": Product,
        "category": Category,
        "supplier": Supplier,
        "customer": Customer,
        "user": User,
    }
    parts = []
    for key, value in filters.items():
        if key in lookups:
            record = lookups[key].objects.filter(pk=value).first()
            value = str(record) if record else f"#{value}"
        elif key == "cutoff":
            value = value.astimezone(business_tz()).strftime("%Y-%m-%d %H:%M (%Z)")
        parts.append(f"{key.replace('_', ' ').title()}: {value}")
    return " · ".join(parts) if parts else "No filters (full dataset)"
