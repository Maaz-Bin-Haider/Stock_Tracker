"""Corrections to received stock that has not moved into downstream workflows.

Purchase lines and collections keep their identities. Their current ledger
contributions are reversed and reposted, so original history remains immutable
and later collection undo uses the corrected product and cost.
"""

from django.db.models import Min
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.inventory.models import Bucket, SourceType, StockBalance, StockLedgerEntry, TxnType
from apps.inventory.services import Movement, PostingError, net_reversal_movements, post_event
from apps.shipments.models import ShipmentLine

MODULE = "purchases"
DEPENDENCIES = {
    SourceType.SALE: "sale",
    SourceType.SHIPMENT: "shipment",
    SourceType.SHIPMENT_RECEIPT: "shipment receiving",
    SourceType.STOCK_ADJUSTMENT: "stock adjustment",
    SourceType.PURCHASE_REFUND: "refund",
}


def correction_block_reason(line):
    """Read-only eligibility for UI hints; checked again inside the stock lock.

    Stock is pooled rather than allocated to purchase lots. Activity affecting
    the same product/collection location after receipt is conservatively treated
    as a dependency, even when a different invoice might have supplied it.
    """
    if line.is_deleted or line.purchase.is_deleted:
        return "This purchase line has been removed."
    if line.refunded_qty > 0:
        return "This line has a refund or cancellation. Product, price and removal are locked."
    if line.collected_qty == 0:
        return ""

    locations = list(
        line.collection_lines.filter(collection__is_deleted=False)
        .values_list(
            "collection__location_id",
            flat=True,
        )
        .distinct()
    )
    first_collection = StockLedgerEntry.objects.filter(
        source_type=SourceType.PURCHASE_COLLECTION,
        source_line_id=line.pk,
        product=line.product,
        bucket=Bucket.PHYSICAL,
        qty_in__gt=0,
    ).aggregate(first_id=Min("id"))["first_id"]
    if first_collection is None:
        return "Collection ledger history is incomplete. Review this line before correcting it."

    dependency = (
        StockLedgerEntry.objects.filter(
            product=line.product,
            location_id__in=locations,
            source_type__in=DEPENDENCIES,
            id__gt=first_collection,
        )
        .select_related("location")
        .order_by("id")
        .first()
    )
    if dependency:
        activity = DEPENDENCIES[dependency.source_type]
        return (
            f"A {activity} affects this product at {dependency.location.name} after collection "
            f"(record #{dependency.source_id}). Product, price and removal are locked "
            "because stock is pooled across invoices."
        )

    draft = (
        ShipmentLine.objects.filter(
            product=line.product,
            is_deleted=False,
            shipment__is_deleted=False,
            shipment__cancelled_at__isnull=True,
            shipment__shipped_at__isnull=True,
            shipment__from_location_id__in=locations,
        )
        .select_related("shipment")
        .first()
    )
    if draft:
        return (
            f"Open shipment {draft.shipment.shipment_no} includes this product. "
            "Resolve that shipment before changing the product, price or removing this line."
        )

    from .services import _physical_remainder_by_location

    held = _physical_remainder_by_location(line)
    if sum(quantity for quantity, _value in held.values()) != line.collected_qty:
        return (
            "Collected stock no longer matches this line. Review its movements before correction."
        )
    for location_id, (quantity, value) in held.items():
        balance = StockBalance.objects.filter(
            product=line.product,
            location_id=location_id,
            bucket=Bucket.PHYSICAL,
        ).first()
        if quantity < 0 or value < 0 or (quantity == 0 and value != 0):
            return "This line has inconsistent physical stock values. Review before correction."
        if quantity and (
            balance is None or balance.quantity < quantity or balance.value_aed < value
        ):
            return "Received stock or value is no longer available for this correction."
    return ""


def _reverse_source(line, source_type, source_id, user):
    entries = StockLedgerEntry.objects.filter(
        source_type=source_type,
        source_id=source_id,
        source_line_id=line.pk,
    ).select_related("product", "location", "related_location")
    try:
        moves = net_reversal_movements(
            entries, notes="Purchase correction: reverse prior contribution."
        )
    except PostingError as exc:
        raise ValidationError({"lines": str(exc)}) from exc
    if moves:
        post_event(
            txn_type=TxnType.EDIT_REVERSAL,
            source_module=MODULE,
            source_type=source_type,
            source_id=source_id,
            movements=moves,
            created_by=user,
        )


def correct_received_line(line, changes, user, *, remove=False):
    """Called only from a serialized stock transaction; never rewrite ledger rows."""
    reason = correction_block_reason(line)
    if reason:
        raise ValidationError({"lines": f"{line.product}: {reason}"})

    collections = list(
        line.collection_lines.filter(collection__is_deleted=False)
        .select_related(
            "collection__location",
        )
        .order_by("collection__created_at", "collection_id", "id")
    )
    for collection_id in dict.fromkeys(item.collection_id for item in collections):
        _reverse_source(line, SourceType.PURCHASE_COLLECTION, collection_id, user)
    _reverse_source(line, SourceType.PURCHASE, line.purchase_id, user)

    if remove:
        line.is_deleted = True
        line.deleted_at = timezone.now()
        line.deleted_by = user
        line.updated_by = user
        line.save(
            update_fields=["is_deleted", "deleted_at", "deleted_by", "updated_by", "updated_at"]
        )
        return

    from .services import _entry_movement, _pending_share, freeze_line_values

    for name, value in changes.items():
        setattr(line, name, value)
    freeze_line_values(line)
    line.updated_by = user
    line.save()
    post_event(
        txn_type=TxnType.EDIT_REVERSAL,
        source_module=MODULE,
        source_type=SourceType.PURCHASE,
        source_id=line.purchase_id,
        movements=[_entry_movement(line, line.quantity, line.total_value_aed, line.gst_amount_aed)],
        created_by=user,
    )
    # Replay the existing business collections, without creating or changing
    # collection quantities. Allocating from pending keeps the final cent exact.
    for item in collections:
        aed, gst = _pending_share(line, item.quantity)
        post_event(
            txn_type=TxnType.EDIT_REVERSAL,
            source_module=MODULE,
            source_type=SourceType.PURCHASE_COLLECTION,
            source_id=item.collection_id,
            created_by=user,
            movements=[
                Movement(
                    product=line.product,
                    location=line.purchase.location,
                    bucket=Bucket.PENDING,
                    qty_out=item.quantity,
                    aed_value=aed,
                    gst_value=gst,
                    currency=line.currency.code,
                    related_location=item.collection.location,
                    source_line_id=line.pk,
                    notes="Purchase correction: replay collection at corrected product and cost.",
                ),
                Movement(
                    product=line.product,
                    location=item.collection.location,
                    bucket=Bucket.PHYSICAL,
                    qty_in=item.quantity,
                    aed_value=aed,
                    currency=line.currency.code,
                    related_location=line.purchase.location,
                    source_line_id=line.pk,
                    notes="Purchase correction: replay received stock.",
                ),
            ],
        )
