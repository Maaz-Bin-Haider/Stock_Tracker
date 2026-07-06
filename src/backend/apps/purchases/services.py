"""Purchase business services: the only path that writes purchases,
collections, and their ledger postings.

Every function runs the business-record write, the ledger post, and the audit
row in one ``transaction.atomic()`` block (SRS §7.3, TECHNICAL_ARCHITECTURE
§5.4). Ledger mapping implemented here (§5.2):

- Purchase line entered      → +PENDING @ purchase location
- Purchase collection        → −PENDING @ purchase location,
                               +PHYSICAL @ collection location
- Refund/cancel pending qty  → −PENDING @ purchase location
- Refund of received qty     → −PHYSICAL @ collection location
                               (AED/GST reversed at the original line rate)
- Edit of a line             → reversal rows for the old pending state
                               + fresh rows for the new state
- Soft delete                → reversal rows only
"""

from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Case, DecimalField, F, Sum, When
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.audits.models import AuditLog
from apps.audits.services import record_audit
from apps.inventory.models import Bucket, StockLedgerEntry, TxnType
from apps.inventory.services import Movement, post_event
from apps.masterdata.models import Location

from .models import (
    Purchase,
    PurchaseCollection,
    PurchaseCollectionLine,
    PurchaseLine,
    PurchaseRefund,
    PurchaseRefundLine,
    RefundSource,
)

TWO_PLACES = Decimal("0.01")
MODULE = "purchases"


def _money(value) -> Decimal:
    return Decimal(value).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def freeze_line_values(line: PurchaseLine) -> None:
    """Compute and freeze AED/GST values at entry time (ADR 7, FR-092)."""
    line.unit_price_aed = _money(line.unit_price * line.exchange_rate)
    line.total_value_aed = _money(line.quantity * line.unit_price * line.exchange_rate)
    gross = line.quantity * line.unit_price
    line.gst_amount = _money(gross * line.gst_rate_percent / 100)
    line.gst_amount_aed = _money(line.gst_amount * line.exchange_rate)


def _pending_remainder(line: PurchaseLine) -> tuple[Decimal, Decimal, Decimal]:
    """(qty, aed, gst) still sitting in PENDING for this line, from the ledger.

    Summing the ledger (entries, collections, edits, reversals) keeps
    proportional value allocation exact — the last movement out of a line's
    pending always carries exactly the remaining value, so no cent residue is
    left behind at zero quantity.
    """
    sums = StockLedgerEntry.objects.filter(
        source_module=MODULE, source_line_id=line.pk, bucket=Bucket.PENDING
    ).aggregate(
        qty=Sum(F("qty_in") - F("qty_out")),
        aed=Sum(
            Case(
                When(qty_in__gt=0, then=F("aed_value")),
                default=F("aed_value") * -1,
                output_field=DecimalField(max_digits=14, decimal_places=2),
            )
        ),
        gst=Sum(
            Case(
                When(qty_in__gt=0, then=F("gst_value")),
                default=F("gst_value") * -1,
                output_field=DecimalField(max_digits=14, decimal_places=2),
            )
        ),
    )
    return (
        sums["qty"] or Decimal("0"),
        sums["aed"] or Decimal("0"),
        sums["gst"] or Decimal("0"),
    )


def _pending_share(line: PurchaseLine, quantity: Decimal) -> tuple[Decimal, Decimal]:
    """AED/GST share of ``quantity`` taken proportionally from the line's
    remaining pending value; exact for the final quantity."""
    remaining_qty, remaining_aed, remaining_gst = _pending_remainder(line)
    if quantity > remaining_qty:
        raise ValidationError(
            {"quantity": f"Only {remaining_qty} pending for {line.product}; got {quantity}."}
        )
    if quantity == remaining_qty:
        return remaining_aed, remaining_gst
    return (
        _money(remaining_aed * quantity / remaining_qty),
        _money(remaining_gst * quantity / remaining_qty),
    )


def _entry_movement(line: PurchaseLine, qty: Decimal, aed: Decimal, gst: Decimal) -> Movement:
    return Movement(
        product=line.product,
        location=line.purchase.location,
        bucket=Bucket.PENDING,
        qty_in=qty,
        aed_value=aed,
        gst_value=gst,
        currency=line.currency.code,
        source_line_id=line.pk,
    )


def _physical_remainder_by_location(line: PurchaseLine) -> dict:
    """{location_id: (qty, aed)} still in PHYSICAL for this line, per the
    ledger — collections in, refunds/reversals out."""
    rows = (
        StockLedgerEntry.objects.filter(
            source_module=MODULE, source_line_id=line.pk, bucket=Bucket.PHYSICAL
        )
        .values("location_id")
        .annotate(
            qty=Sum(F("qty_in") - F("qty_out")),
            aed=Sum(
                Case(
                    When(qty_in__gt=0, then=F("aed_value")),
                    default=F("aed_value") * -1,
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                )
            ),
        )
    )
    return {
        row["location_id"]: (row["qty"] or Decimal("0"), row["aed"] or Decimal("0"))
        for row in rows
    }


def _physical_share(line: PurchaseLine, location, quantity: Decimal) -> Decimal:
    """AED share of ``quantity`` from the line's physical remainder at the
    location; proportional, exact for the final quantity."""
    remaining_qty, remaining_aed = _physical_remainder_by_location(line).get(
        location.pk, (Decimal("0"), Decimal("0"))
    )
    if quantity > remaining_qty:
        raise ValidationError(
            {
                "quantity": (
                    f"Only {remaining_qty} of {line.product} is in stock at {location} "
                    f"from this purchase line; cannot refund {quantity}."
                )
            }
        )
    if quantity == remaining_qty:
        return remaining_aed
    return _money(remaining_aed * quantity / remaining_qty)


@transaction.atomic
def create_purchase(*, header: dict, lines: list[dict], user) -> Purchase:
    """Create invoice + lines, post +PENDING per line, and immediately collect
    any line quantities entered as already collected (activity diagram 2.2)."""
    purchase = Purchase.objects.create(created_by=user, updated_by=user, **header)

    initial_collections = []
    movements = []
    for line_data in lines:
        initial_qty = line_data.pop("collected_qty", None) or Decimal("0")
        line = PurchaseLine(purchase=purchase, created_by=user, updated_by=user, **line_data)
        freeze_line_values(line)
        line.save()
        movements.append(
            _entry_movement(line, line.quantity, line.total_value_aed, line.gst_amount_aed)
        )
        if initial_qty:
            initial_collections.append((line, initial_qty))

    post_event(
        txn_type=TxnType.PURCHASE_ENTRY,
        source_module=MODULE,
        source_id=purchase.pk,
        movements=movements,
        created_by=user,
    )
    record_audit(
        action=AuditLog.Action.CREATE,
        module=MODULE,
        record_id=purchase.pk,
        record_repr=str(purchase),
        after=snapshot_purchase(purchase),
    )

    if initial_collections:
        collect_purchase(
            purchase=purchase,
            collection_date=purchase.purchase_date,
            location=purchase.location,
            lines=[
                {"purchase_line": line, "quantity": qty} for line, qty in initial_collections
            ],
            notes="Collected at purchase entry.",
            user=user,
        )
    return purchase


@transaction.atomic
def collect_purchase(
    *, purchase: Purchase, collection_date, location, lines: list[dict], notes="", user
) -> PurchaseCollection:
    """Partial/product-wise collection (FR-040/FR-041): −PENDING at the
    purchase location, +PHYSICAL at the collection location (FR-042)."""
    if purchase.is_deleted:
        raise ValidationError({"purchase": "This purchase has been deleted."})
    if not lines:
        raise ValidationError({"lines": "At least one line is required."})

    collection = PurchaseCollection.objects.create(
        purchase=purchase,
        collection_date=collection_date,
        location=location,
        notes=notes,
        created_by=user,
        updated_by=user,
    )
    movements = []
    for line_data in lines:
        line: PurchaseLine = line_data["purchase_line"]
        quantity: Decimal = line_data["quantity"]
        if line.purchase_id != purchase.pk or line.is_deleted:
            raise ValidationError({"lines": f"Line {line.pk} does not belong to this purchase."})
        if quantity <= 0:
            raise ValidationError({"quantity": "Collected quantity must be positive."})
        if quantity > line.pending_qty:
            raise ValidationError(
                {
                    "quantity": (
                        f"Cannot collect {quantity} of {line.product}: "
                        f"only {line.pending_qty} pending."
                    )
                }
            )
        PurchaseCollectionLine.objects.create(
            collection=collection, purchase_line=line, quantity=quantity
        )
        # gst on the −PENDING row is bucket bookkeeping only (it keeps
        # _pending_remainder exact for later edits/cancellations); GST
        # liability itself lives on the PURCHASE_ENTRY rows and the purchase
        # lines — reports must never sum gst_value across all ledger rows.
        aed, gst = _pending_share(line, quantity)
        movements.append(
            Movement(
                product=line.product,
                location=purchase.location,
                bucket=Bucket.PENDING,
                qty_out=quantity,
                aed_value=aed,
                gst_value=gst,
                currency=line.currency.code,
                related_location=location,
                source_line_id=line.pk,
            )
        )
        movements.append(
            Movement(
                product=line.product,
                location=location,
                bucket=Bucket.PHYSICAL,
                qty_in=quantity,
                aed_value=aed,
                currency=line.currency.code,
                related_location=purchase.location,
                source_line_id=line.pk,
            )
        )

    post_event(
        txn_type=TxnType.PURCHASE_COLLECTION,
        source_module=MODULE,
        source_id=collection.pk,
        movements=movements,
        created_by=user,
    )
    record_audit(
        action=AuditLog.Action.CREATE,
        module="purchase_collections",
        record_id=collection.pk,
        record_repr=str(collection),
        after=snapshot_collection(collection),
    )
    return collection


@transaction.atomic
def update_purchase(*, purchase: Purchase, header: dict, lines: list[dict], user) -> Purchase:
    """Header edits are plain audited updates; stock-affecting line edits post
    reversal rows for the old pending state + fresh rows for the new (§5.2,
    FR-081). Lines with collected stock keep pricing immutable — quantity may
    only grow or shrink down to the collected amount."""
    if purchase.is_deleted:
        raise ValidationError({"purchase": "This purchase has been deleted."})
    before = snapshot_purchase(purchase)

    if "location" in header and header["location"] != purchase.location:
        raise ValidationError(
            {"location": "Purchase location cannot change after entry; delete and re-enter."}
        )
    for field_name, value in header.items():
        setattr(purchase, field_name, value)
    purchase.updated_by = user
    purchase.save()

    existing = {line.pk: line for line in purchase.lines.filter(is_deleted=False)}
    seen_ids = set()
    movements = []

    for line_data in lines:
        line_id = line_data.pop("id", None)
        line_data.pop("collected_qty", None)  # collection is its own workflow after entry
        if line_id is None:
            line = PurchaseLine(purchase=purchase, created_by=user, updated_by=user, **line_data)
            freeze_line_values(line)
            line.save()
            movements.append(
                _entry_movement(line, line.quantity, line.total_value_aed, line.gst_amount_aed)
            )
            continue

        line = existing.get(line_id)
        if line is None:
            raise ValidationError({"lines": f"Line {line_id} does not belong to this purchase."})
        seen_ids.add(line_id)
        movements.extend(_reprice_line(line, line_data, user))

    for line in existing.values():
        if line.pk not in seen_ids:
            movements.extend(_remove_line(line, user))

    if movements:
        post_event(
            txn_type=TxnType.EDIT_REVERSAL,
            source_module=MODULE,
            source_id=purchase.pk,
            movements=movements,
            created_by=user,
        )
    record_audit(
        action=AuditLog.Action.UPDATE,
        module=MODULE,
        record_id=purchase.pk,
        record_repr=str(purchase),
        before=before,
        after=snapshot_purchase(purchase),
    )
    return purchase


PRICING_FIELDS = ("product", "unit_price", "currency", "exchange_rate", "gst_rate_percent")


def _reprice_line(line: PurchaseLine, line_data: dict, user) -> list[Movement]:
    """Apply an edit to one line, returning reversal + fresh pending movements."""
    collected = line.collected_qty
    cancelled_pending = line.cancelled_pending_qty
    changed = {
        name: value
        for name, value in line_data.items()
        if getattr(line, name) != value and name != "notes"
    }
    if "notes" in line_data:
        line.notes = line_data["notes"]

    if not changed:
        line.updated_by = user
        line.save()
        return []

    if collected > 0 or line.refunded_qty > 0:
        illegal = [name for name in changed if name in PRICING_FIELDS or name == "gst_rate"]
        if illegal:
            raise ValidationError(
                {
                    "lines": (
                        f"{line.product}: {', '.join(illegal)} cannot change after stock was "
                        "collected or refunded. Use refund/cancellation, or adjust quantity only."
                    )
                }
            )
    new_quantity = changed.get("quantity", line.quantity)
    floor = collected + cancelled_pending
    if new_quantity < floor:
        raise ValidationError(
            {
                "quantity": (
                    f"{line.product}: quantity {new_quantity} is below collected + "
                    f"cancelled ({floor})."
                )
            }
        )

    # Reverse what remains in pending for the old state.
    movements = []
    remaining_qty, remaining_aed, remaining_gst = _pending_remainder(line)
    if remaining_qty > 0:
        movements.append(
            Movement(
                product=line.product,
                location=line.purchase.location,
                bucket=Bucket.PENDING,
                qty_out=remaining_qty,
                aed_value=remaining_aed,
                gst_value=remaining_gst,
                currency=line.currency.code,
                source_line_id=line.pk,
                notes="Edit reversal of prior pending state.",
            )
        )

    for name, value in changed.items():
        setattr(line, name, value)
    freeze_line_values(line)
    line.updated_by = user
    line.save()

    # Fresh pending rows for the new state: the uncollected, uncancelled part
    # of the line, valued at the (possibly new) frozen line pricing.
    fresh_qty = line.quantity - collected - cancelled_pending
    if fresh_qty > 0:
        ratio = fresh_qty / line.quantity
        movements.append(
            _entry_movement(
                line,
                fresh_qty,
                _money(line.total_value_aed * ratio),
                _money(line.gst_amount_aed * ratio),
            )
        )
    return movements


def _remove_line(line: PurchaseLine, user) -> list[Movement]:
    """Soft-delete a line during an invoice edit; reversal rows only (§5.2)."""
    if line.collected_qty > 0 or line.refunded_qty > 0:
        raise ValidationError(
            {
                "lines": (
                    f"{line.product}: line has collection or refund history and cannot be "
                    "removed from the invoice. Use refund/cancellation instead."
                )
            }
        )
    movements = []
    remaining_qty, remaining_aed, remaining_gst = _pending_remainder(line)
    if remaining_qty > 0:
        movements.append(
            Movement(
                product=line.product,
                location=line.purchase.location,
                bucket=Bucket.PENDING,
                qty_out=remaining_qty,
                aed_value=remaining_aed,
                gst_value=remaining_gst,
                currency=line.currency.code,
                source_line_id=line.pk,
                notes="Line removed from invoice.",
            )
        )
    line.is_deleted = True
    line.deleted_at = timezone.now()
    line.deleted_by = user
    line.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])
    return movements


@transaction.atomic
def soft_delete_purchase(*, purchase: Purchase, user, confirm_negative=False) -> None:
    """Soft delete: reversal rows only (§5.2) — remaining pending is backed
    out and collected physical stock is reversed. History stays traceable."""
    if purchase.is_deleted:
        raise ValidationError({"purchase": "This purchase is already deleted."})
    before = snapshot_purchase(purchase)
    now = timezone.now()

    movements = []
    for line in purchase.lines.filter(is_deleted=False):
        remaining_qty, remaining_aed, remaining_gst = _pending_remainder(line)
        if remaining_qty > 0:
            movements.append(
                Movement(
                    product=line.product,
                    location=purchase.location,
                    bucket=Bucket.PENDING,
                    qty_out=remaining_qty,
                    aed_value=remaining_aed,
                    gst_value=remaining_gst,
                    currency=line.currency.code,
                    source_line_id=line.pk,
                    notes="Purchase deleted.",
                )
            )
        for location_id, (qty, aed) in _physical_remainder_by_location(line).items():
            if qty <= 0:
                continue
            movements.append(
                Movement(
                    product=line.product,
                    location=Location.objects.get(pk=location_id),
                    bucket=Bucket.PHYSICAL,
                    qty_out=qty,
                    aed_value=aed,
                    currency=line.currency.code,
                    source_line_id=line.pk,
                    notes="Purchase deleted.",
                )
            )
        line.is_deleted, line.deleted_at, line.deleted_by = True, now, user
        line.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])

    for collection in purchase.collections.filter(is_deleted=False):
        collection.is_deleted, collection.deleted_at, collection.deleted_by = True, now, user
        collection.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])

    for refund in purchase.refunds.filter(is_deleted=False):
        refund.is_deleted, refund.deleted_at, refund.deleted_by = True, now, user
        refund.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])

    if movements:
        post_event(
            txn_type=TxnType.DELETE_REVERSAL,
            source_module=MODULE,
            source_id=purchase.pk,
            movements=movements,
            created_by=user,
            confirm_negative=confirm_negative,
        )

    purchase.is_deleted, purchase.deleted_at, purchase.deleted_by = True, now, user
    purchase.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])
    record_audit(
        action=AuditLog.Action.DELETE,
        module=MODULE,
        record_id=purchase.pk,
        record_repr=str(purchase),
        before=before,
    )


@transaction.atomic
def delete_collection(*, collection: PurchaseCollection, user, confirm_negative=False) -> None:
    """Undo a collection: +PENDING back, −PHYSICAL out, soft delete (§5.2)."""
    if collection.is_deleted:
        raise ValidationError({"collection": "This collection is already deleted."})
    before = snapshot_collection(collection)

    entries = StockLedgerEntry.objects.filter(
        source_module=MODULE,
        txn_type=TxnType.PURCHASE_COLLECTION,
        source_id=collection.pk,
    )
    from apps.inventory.services import reversal_movements

    movements = reversal_movements(entries, notes="Collection deleted.")

    collection.is_deleted = True
    collection.deleted_at = timezone.now()
    collection.deleted_by = user
    collection.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])

    if movements:
        post_event(
            txn_type=TxnType.DELETE_REVERSAL,
            source_module=MODULE,
            source_id=collection.pk,
            movements=movements,
            created_by=user,
            confirm_negative=confirm_negative,
        )
    record_audit(
        action=AuditLog.Action.DELETE,
        module="purchase_collections",
        record_id=collection.pk,
        record_repr=str(collection),
        before=before,
    )


@transaction.atomic
def create_refund(
    *,
    purchase: Purchase,
    refund_date,
    reason: str,
    lines: list[dict],
    notes="",
    refund_no="",
    user,
    confirm_negative=False,
) -> PurchaseRefund:
    """Line-level partial refund/cancellation (FR-047/FR-048).

    PENDING source cancels undelivered quantity (−PENDING at the purchase
    location); RECEIVED source returns delivered stock (−PHYSICAL at the
    location holding it). AED and GST reverse at the original purchase line
    rate, frozen onto the refund line for the GST/refund reports
    (FR-053/FR-054/FR-093/FR-122).
    """
    if purchase.is_deleted:
        raise ValidationError({"purchase": "This purchase has been deleted."})
    if not lines:
        raise ValidationError({"lines": "At least one line is required."})
    if not reason.strip():
        raise ValidationError({"reason": "A reason is required."})

    refund = PurchaseRefund.objects.create(
        purchase=purchase,
        refund_no=refund_no,
        refund_date=refund_date,
        reason=reason,
        notes=notes,
        created_by=user,
        updated_by=user,
    )
    if not refund.refund_no:
        refund.refund_no = f"RF-{refund.pk:06d}"
        refund.save(update_fields=["refund_no"])

    movements = []
    for line_data in lines:
        line: PurchaseLine = line_data["purchase_line"]
        source: str = line_data["source"]
        quantity: Decimal = line_data["quantity"]
        if line.purchase_id != purchase.pk or line.is_deleted:
            raise ValidationError({"lines": f"Line {line.pk} does not belong to this purchase."})
        if quantity <= 0:
            raise ValidationError({"quantity": "Refund quantity must be positive."})

        # Original-line-rate reversal values, frozen for reporting.
        value_reversal = _money(quantity * line.unit_price)
        value_reversal_aed = _money(value_reversal * line.exchange_rate)
        gst_reversal = _money(quantity * line.unit_price * line.gst_rate_percent / 100)
        gst_reversal_aed = _money(gst_reversal * line.exchange_rate)

        if source == RefundSource.PENDING:
            location = purchase.location
            if quantity > line.pending_qty:
                raise ValidationError(
                    {
                        "quantity": (
                            f"Only {line.pending_qty} of {line.product} is pending; "
                            f"cannot cancel {quantity}."
                        )
                    }
                )
            # Ledger share keeps the pending bucket exact (zero when emptied).
            aed_share, gst_share = _pending_share(line, quantity)
            movements.append(
                Movement(
                    product=line.product,
                    location=location,
                    bucket=Bucket.PENDING,
                    qty_out=quantity,
                    aed_value=aed_share,
                    gst_value=gst_share,
                    currency=line.currency.code,
                    source_line_id=line.pk,
                    notes=f"Cancelled: {reason}"[:255],
                )
            )
        elif source == RefundSource.RECEIVED:
            location = line_data.get("location") or purchase.location
            aed_share = _physical_share(line, location, quantity)
            movements.append(
                Movement(
                    product=line.product,
                    location=location,
                    bucket=Bucket.PHYSICAL,
                    qty_out=quantity,
                    aed_value=aed_share,
                    # Informational: GST reversal at the original line rate.
                    # Net GST reporting reads purchase/refund lines, never
                    # ledger gst sums (see collect_purchase note).
                    gst_value=gst_reversal_aed,
                    currency=line.currency.code,
                    source_line_id=line.pk,
                    notes=f"Refunded: {reason}"[:255],
                )
            )
        else:
            raise ValidationError({"source": f"Unknown refund source {source!r}."})

        PurchaseRefundLine.objects.create(
            refund=refund,
            purchase_line=line,
            source=source,
            quantity=quantity,
            location=location,
            value_reversal=value_reversal,
            value_reversal_aed=value_reversal_aed,
            gst_reversal=gst_reversal,
            gst_reversal_aed=gst_reversal_aed,
        )

    post_event(
        txn_type=TxnType.PURCHASE_REFUND,
        source_module=MODULE,
        source_id=refund.pk,
        movements=movements,
        created_by=user,
        confirm_negative=confirm_negative,
    )
    record_audit(
        action=AuditLog.Action.CREATE,
        module="purchase_refunds",
        record_id=refund.pk,
        record_repr=str(refund),
        after=snapshot_refund(refund),
    )
    return refund


@transaction.atomic
def delete_refund(*, refund: PurchaseRefund, user, confirm_negative=False) -> None:
    """Undo a refund: its reversal entries are themselves reversed (history
    preserved), and the refund is soft-deleted."""
    if refund.is_deleted:
        raise ValidationError({"refund": "This refund is already deleted."})
    before = snapshot_refund(refund)

    entries = StockLedgerEntry.objects.filter(
        source_module=MODULE,
        txn_type=TxnType.PURCHASE_REFUND,
        source_id=refund.pk,
    )
    from apps.inventory.services import reversal_movements

    movements = reversal_movements(entries, notes="Refund deleted.")

    refund.is_deleted = True
    refund.deleted_at = timezone.now()
    refund.deleted_by = user
    refund.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])

    if movements:
        post_event(
            txn_type=TxnType.DELETE_REVERSAL,
            source_module=MODULE,
            source_id=refund.pk,
            movements=movements,
            created_by=user,
            confirm_negative=confirm_negative,
        )
    record_audit(
        action=AuditLog.Action.DELETE,
        module="purchase_refunds",
        record_id=refund.pk,
        record_repr=str(refund),
        before=before,
    )


def snapshot_refund(refund: PurchaseRefund) -> dict:
    return {
        "refund_no": refund.refund_no,
        "purchase": refund.purchase.invoice_no,
        "refund_date": str(refund.refund_date),
        "reason": refund.reason,
        "notes": refund.notes,
        "lines": [
            {
                "purchase_line": line.purchase_line_id,
                "product": str(line.purchase_line.product),
                "source": line.source,
                "quantity": str(line.quantity),
                "location": line.location.name,
                "value_reversal": str(line.value_reversal),
                "value_reversal_aed": str(line.value_reversal_aed),
                "gst_reversal": str(line.gst_reversal),
                "gst_reversal_aed": str(line.gst_reversal_aed),
            }
            for line in refund.lines.all()
        ],
    }


def snapshot_purchase(purchase: Purchase) -> dict:
    return {
        "invoice_no": purchase.invoice_no,
        "purchase_date": str(purchase.purchase_date),
        "location": purchase.location.name,
        "supplier": purchase.supplier.name,
        "notes": purchase.notes,
        "status": purchase.status,
        "lines": [
            {
                "id": line.pk,
                "product": str(line.product),
                "quantity": str(line.quantity),
                "unit_price": str(line.unit_price),
                "currency": line.currency.code,
                "exchange_rate": str(line.exchange_rate),
                "total_value_aed": str(line.total_value_aed),
                "gst_rate_percent": str(line.gst_rate_percent),
                "gst_amount": str(line.gst_amount),
                "collected_qty": str(line.collected_qty),
                "pending_qty": str(line.pending_qty),
                "refunded_qty": str(line.refunded_qty),
                "net_qty": str(line.net_qty),
                "status": line.status,
                "notes": line.notes,
            }
            for line in purchase.lines.filter(is_deleted=False)
        ],
    }


def snapshot_collection(collection: PurchaseCollection) -> dict:
    return {
        "purchase": collection.purchase.invoice_no,
        "collection_date": str(collection.collection_date),
        "location": collection.location.name,
        "notes": collection.notes,
        "lines": [
            {
                "purchase_line": line.purchase_line_id,
                "product": str(line.purchase_line.product),
                "quantity": str(line.quantity),
            }
            for line in collection.lines.all()
        ],
    }
