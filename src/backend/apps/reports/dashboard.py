"""Dashboard aggregates (FR-094…FR-096).

Live cards read ``stock_balances``; a past cutoff aggregates the ledger with
``txn_at <= cutoff`` instead (TECHNICAL_ARCHITECTURE §5.3). GST comes from the
values frozen on purchase/refund lines — never from summing ledger
``gst_value`` rows. Every "today" boundary is Dubai business time (FR-128).
"""

from decimal import Decimal

from django.db.models import Q, Sum
from django.utils import timezone

from apps.core.time import business_tz
from apps.inventory.models import Bucket
from apps.masterdata.models import Location
from apps.purchases.models import PurchaseLine, PurchaseRefundLine
from apps.sales.models import SaleLine

from .builders import balance_map

ZERO = Decimal("0.00")


def _existing_at(queryset, cutoff, created_field="created_at"):
    """Records that existed (and were not yet soft-deleted) at the cutoff.
    Without a cutoff: current non-deleted records."""
    if cutoff is None:
        return queryset.filter(is_deleted=False)
    return queryset.filter(**{f"{created_field}__lte": cutoff}).filter(
        Q(is_deleted=False) | Q(deleted_at__gt=cutoff)
    )


def _gst_total(cutoff) -> Decimal:
    """Net GST in AED: purchase-line GST minus refund reversals (FR-093)."""
    # Header deletion soft-deletes its lines too, so line-level flags suffice.
    purchased = _existing_at(PurchaseLine.objects.all(), cutoff)
    gst = purchased.aggregate(total=Sum("gst_amount_aed"))["total"] or ZERO

    refund_lines = PurchaseRefundLine.objects.all()
    if cutoff is None:
        refund_lines = refund_lines.filter(refund__is_deleted=False)
    else:
        refund_lines = refund_lines.filter(refund__created_at__lte=cutoff).filter(
            Q(refund__is_deleted=False) | Q(refund__deleted_at__gt=cutoff)
        )
    reversed_gst = refund_lines.aggregate(total=Sum("gst_reversal_aed"))["total"] or ZERO
    return gst - reversed_gst


def _todays_sales(business_date, cutoff) -> dict:
    lines = _existing_at(SaleLine.objects.all(), cutoff).filter(
        sale__sale_date=business_date
    )
    if cutoff is None:
        lines = lines.filter(sale__is_deleted=False)
    aggregate = lines.aggregate(quantity=Sum("quantity"))
    return {
        "quantity": aggregate["quantity"] or ZERO,
        "lines": lines.count(),
    }


def dashboard_data(cutoff=None) -> dict:
    balances = balance_map({"cutoff": cutoff})

    bucket_totals = {bucket: ZERO for bucket in Bucket.values}
    by_location: dict[int, dict] = {}
    for (_product_id, location_id), buckets in balances.items():
        location_agg = by_location.setdefault(
            location_id, {bucket: ZERO for bucket in Bucket.values}
        )
        for bucket, (quantity, _value) in buckets.items():
            bucket_totals[bucket] += quantity
            location_agg[bucket] += quantity

    locations = {location.pk: location for location in Location.objects.filter(is_active=True)}
    stock_by_location = [
        {
            "location": locations[location_id].name,
            "physical": agg[Bucket.PHYSICAL],
            "pending": agg[Bucket.PENDING],
            "in_transit": agg[Bucket.IN_TRANSIT],
        }
        for location_id, agg in by_location.items()
        if location_id in locations
    ]
    stock_by_location.sort(key=lambda row: row["location"])

    sales_location_cards = [
        {
            "location": location.name,
            "physical": by_location.get(location.pk, {}).get(Bucket.PHYSICAL, ZERO),
            "in_transit": by_location.get(location.pk, {}).get(Bucket.IN_TRANSIT, ZERO),
        }
        for location in sorted(
            (loc for loc in locations.values() if loc.is_sales_location),
            key=lambda loc: loc.name,
        )
    ]

    moment = cutoff or timezone.now()
    business_date = moment.astimezone(business_tz()).date()

    return {
        "as_of": cutoff,
        "business_date": business_date,
        "cards": {
            "total_physical": bucket_totals[Bucket.PHYSICAL],
            "total_pending": bucket_totals[Bucket.PENDING],
            "total_in_transit": bucket_totals[Bucket.IN_TRANSIT],
            "gst_total_aed": _gst_total(cutoff),
            "todays_sales": _todays_sales(business_date, cutoff),
            "sales_locations": sales_location_cards,
        },
        "stock_by_location": stock_by_location,
    }
