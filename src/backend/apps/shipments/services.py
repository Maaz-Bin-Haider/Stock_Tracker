"""Shipment business services: the only path that writes shipments, receipts,
and their ledger postings.

Every function runs the business-record write, the ledger post, and the audit
row in one ``transaction.atomic()`` block (SRS §7.3, TECHNICAL_ARCHITECTURE
§5.4). Ledger mapping implemented here (§5.2):

- Shipment marked shipped → −PHYSICAL @ from-location, +IN_TRANSIT @ to-location
- Shipment receipt       → −IN_TRANSIT @ to-location, +PHYSICAL @ to-location
- Shipment cancelled     → reversal of the unreceived shipped quantities
- Receipt/shipment delete → reversal rows only

Value moves at the source location's carrying average cost from
``stock_balances`` (§5.3.1) — the first flow that consumes carrying value
rather than line-frozen purchase values. Shipping cost never enters stock
value (FR-119); shipments carry no currency (FR-066).
"""

from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Case, DecimalField, F, Sum, When
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.audits.models import AuditLog
from apps.audits.services import record_audit
from apps.inventory.models import Bucket, StockBalance, StockLedgerEntry, TxnType
from apps.inventory.services import Movement, post_event, reversal_movements

from .models import Shipment, ShipmentLine, ShipmentReceipt, ShipmentReceiptLine

TWO_PLACES = Decimal("0.01")
MODULE = "shipments"


def _money(value) -> Decimal:
    return Decimal(value).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def _validate_lines(lines: list[dict]) -> None:
    if not lines:
        raise ValidationError({"lines": "At least one line is required."})
    for line_data in lines:
        if line_data["quantity"] <= 0:
            raise ValidationError({"quantity": "Shipped quantity must be positive."})


@transaction.atomic
def create_shipment(
    *, header: dict, lines: list[dict], ship=False, user, confirm_negative=False
) -> Shipment:
    """Create a draft shipment; optionally mark it shipped immediately."""
    if header["from_location"] == header["to_location"]:
        raise ValidationError({"to_location": "Destination must differ from the source."})
    _validate_lines(lines)

    shipment = Shipment.objects.create(created_by=user, updated_by=user, **header)
    if not shipment.shipment_no:
        shipment.shipment_no = f"SH-{shipment.pk:06d}"
        shipment.save(update_fields=["shipment_no"])
    for line_data in lines:
        ShipmentLine.objects.create(
            shipment=shipment, created_by=user, updated_by=user, **line_data
        )

    record_audit(
        action=AuditLog.Action.CREATE,
        module=MODULE,
        record_id=shipment.pk,
        record_repr=str(shipment),
        after=snapshot_shipment(shipment),
    )
    if ship:
        ship_shipment(shipment=shipment, user=user, confirm_negative=confirm_negative)
    return shipment


def _transit_share(line: ShipmentLine, quantity: Decimal) -> Decimal:
    """AED share of ``quantity`` from the line's in-transit remainder, per the
    ledger. Exact when the remainder is emptied; over-received quantity beyond
    the remainder carries no extra value (value is conserved — the destination
    receives exactly what left the source)."""
    sums = StockLedgerEntry.objects.filter(
        source_module=MODULE, source_line_id=line.pk, bucket=Bucket.IN_TRANSIT
    ).aggregate(
        qty=Sum(F("qty_in") - F("qty_out")),
        aed=Sum(
            Case(
                When(qty_in__gt=0, then=F("aed_value")),
                default=F("aed_value") * -1,
                output_field=DecimalField(max_digits=14, decimal_places=2),
            )
        ),
    )
    remaining_qty = sums["qty"] or Decimal("0")
    remaining_aed = sums["aed"] or Decimal("0")
    if remaining_qty <= 0 or remaining_aed <= 0:
        return Decimal("0.00")
    if quantity >= remaining_qty:
        return remaining_aed
    return _money(remaining_aed * quantity / remaining_qty)


@transaction.atomic
def ship_shipment(*, shipment: Shipment, user, confirm_negative=False) -> Shipment:
    """Mark shipped (FR-063): −PHYSICAL @ from-location, +IN_TRANSIT @
    to-location, valued at the source's carrying average cost (§5.3.1).

    Negative source stock requires explicit confirmation (FR-083).
    """
    if shipment.is_deleted:
        raise ValidationError({"shipment": "This shipment has been deleted."})
    if shipment.cancelled_at:
        raise ValidationError({"shipment": "This shipment is cancelled."})
    if shipment.shipped_at:
        raise ValidationError({"shipment": "This shipment is already shipped."})
    lines = list(shipment.lines.filter(is_deleted=False))
    if not lines:
        raise ValidationError({"lines": "Cannot ship a shipment with no lines."})
    before = snapshot_shipment(shipment)

    # Carrying value drawn per product from the source PHYSICAL pool; a local
    # running remainder keeps multi-line shipments of the same product exact
    # (proportional, and the pool empties to exactly zero value).
    remainders: dict[int, tuple[Decimal, Decimal]] = {}
    movements = []
    for line in lines:
        if line.product_id not in remainders:
            balance = StockBalance.objects.filter(
                product_id=line.product_id,
                location=shipment.from_location,
                bucket=Bucket.PHYSICAL,
            ).first()
            remainders[line.product_id] = (
                (balance.quantity, balance.value_aed) if balance else (Decimal("0"), Decimal("0"))
            )
        pool_qty, pool_aed = remainders[line.product_id]
        if pool_qty <= 0 or pool_aed <= 0:
            aed = Decimal("0.00")
        elif line.quantity >= pool_qty:
            aed = pool_aed
        else:
            aed = _money(pool_aed * line.quantity / pool_qty)
        remainders[line.product_id] = (pool_qty - line.quantity, pool_aed - aed)

        movements.append(
            Movement(
                product=line.product,
                location=shipment.from_location,
                bucket=Bucket.PHYSICAL,
                qty_out=line.quantity,
                aed_value=aed,
                related_location=shipment.to_location,
                source_line_id=line.pk,
            )
        )
        movements.append(
            Movement(
                product=line.product,
                location=shipment.to_location,
                bucket=Bucket.IN_TRANSIT,
                qty_in=line.quantity,
                aed_value=aed,
                related_location=shipment.from_location,
                source_line_id=line.pk,
            )
        )

    shipment.shipped_at = timezone.now()
    shipment.updated_by = user
    shipment.save(update_fields=["shipped_at", "updated_by", "updated_at"])

    post_event(
        txn_type=TxnType.SHIPMENT_OUT,
        source_module=MODULE,
        source_id=shipment.pk,
        movements=movements,
        created_by=user,
        confirm_negative=confirm_negative,
    )
    record_audit(
        action=AuditLog.Action.UPDATE,
        module=MODULE,
        record_id=shipment.pk,
        record_repr=str(shipment),
        before=before,
        after=snapshot_shipment(shipment),
    )
    return shipment


@transaction.atomic
def update_shipment(*, shipment: Shipment, header: dict, lines: list[dict], user) -> Shipment:
    """Draft shipments are freely editable (nothing is posted yet). Once
    shipped, lines are locked — cancel and re-create to change them; only
    header notes/shipping cost/date may change."""
    if shipment.is_deleted:
        raise ValidationError({"shipment": "This shipment has been deleted."})
    if shipment.cancelled_at:
        raise ValidationError({"shipment": "This shipment is cancelled."})
    before = snapshot_shipment(shipment)

    if shipment.shipped_at:
        for field_name in ("from_location", "to_location"):
            if field_name in header and header[field_name] != getattr(shipment, field_name):
                raise ValidationError(
                    {field_name: "Locations cannot change after shipping; cancel and re-enter."}
                )
    elif header.get("from_location", shipment.from_location) == header.get(
        "to_location", shipment.to_location
    ):
        raise ValidationError({"to_location": "Destination must differ from the source."})

    for field_name, value in header.items():
        setattr(shipment, field_name, value)
    shipment.updated_by = user
    shipment.save()

    existing = {line.pk: line for line in shipment.lines.filter(is_deleted=False)}
    if shipment.shipped_at:
        changed = len(lines) != len(existing) or any(
            line_data.get("id") not in existing
            or existing[line_data["id"]].product_id != line_data["product"].pk
            or existing[line_data["id"]].quantity != line_data["quantity"]
            for line_data in lines
        )
        if changed:
            raise ValidationError(
                {"lines": "Shipped lines cannot change; cancel the shipment and re-enter."}
            )
        for line_data in lines:
            line = existing[line_data["id"]]
            if "notes" in line_data and line.notes != line_data["notes"]:
                line.notes = line_data["notes"]
                line.updated_by = user
                line.save(update_fields=["notes", "updated_by", "updated_at"])
    else:
        _validate_lines(lines)
        seen = set()
        for line_data in lines:
            line_id = line_data.pop("id", None)
            if line_id is None:
                ShipmentLine.objects.create(
                    shipment=shipment, created_by=user, updated_by=user, **line_data
                )
                continue
            line = existing.get(line_id)
            if line is None:
                raise ValidationError(
                    {"lines": f"Line {line_id} does not belong to this shipment."}
                )
            seen.add(line_id)
            for field_name, value in line_data.items():
                setattr(line, field_name, value)
            line.updated_by = user
            line.save()
        now = timezone.now()
        for line in existing.values():
            if line.pk not in seen:
                line.is_deleted, line.deleted_at, line.deleted_by = True, now, user
                line.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])

    record_audit(
        action=AuditLog.Action.UPDATE,
        module=MODULE,
        record_id=shipment.pk,
        record_repr=str(shipment),
        before=before,
        after=snapshot_shipment(shipment),
    )
    return shipment


@transaction.atomic
def receive_shipment(
    *, shipment: Shipment, receipt_date, lines: list[dict], notes="", user
) -> ShipmentReceipt:
    """Product-wise partial receiving (FR-061/FR-064): −IN_TRANSIT and
    +PHYSICAL at the destination. Over-receiving is allowed — IN_TRANSIT may
    go negative for the line, which drives the over_received warning
    (FR-084/FR-085, §5.2 note)."""
    if shipment.is_deleted:
        raise ValidationError({"shipment": "This shipment has been deleted."})
    if shipment.cancelled_at:
        raise ValidationError({"shipment": "This shipment is cancelled."})
    if not shipment.shipped_at:
        raise ValidationError({"shipment": "This shipment has not been shipped yet."})
    if not lines:
        raise ValidationError({"lines": "At least one line is required."})

    receipt = ShipmentReceipt.objects.create(
        shipment=shipment,
        receipt_date=receipt_date,
        notes=notes,
        created_by=user,
        updated_by=user,
    )
    movements = []
    for line_data in lines:
        line: ShipmentLine = line_data["shipment_line"]
        quantity: Decimal = line_data["quantity"]
        if line.shipment_id != shipment.pk or line.is_deleted:
            raise ValidationError({"lines": f"Line {line.pk} does not belong to this shipment."})
        if quantity <= 0:
            raise ValidationError({"quantity": "Received quantity must be positive."})

        ShipmentReceiptLine.objects.create(
            receipt=receipt, shipment_line=line, quantity=quantity
        )
        aed = _transit_share(line, quantity)
        movements.append(
            Movement(
                product=line.product,
                location=shipment.to_location,
                bucket=Bucket.IN_TRANSIT,
                qty_out=quantity,
                aed_value=aed,
                related_location=shipment.from_location,
                source_line_id=line.pk,
            )
        )
        movements.append(
            Movement(
                product=line.product,
                location=shipment.to_location,
                bucket=Bucket.PHYSICAL,
                qty_in=quantity,
                aed_value=aed,
                related_location=shipment.from_location,
                source_line_id=line.pk,
            )
        )

    post_event(
        txn_type=TxnType.SHIPMENT_RECEIPT,
        source_module=MODULE,
        source_id=receipt.pk,
        movements=movements,
        created_by=user,
    )
    record_audit(
        action=AuditLog.Action.CREATE,
        module="shipment_receipts",
        record_id=receipt.pk,
        record_repr=str(receipt),
        after=snapshot_receipt(receipt),
    )
    return receipt


@transaction.atomic
def delete_receipt(*, receipt: ShipmentReceipt, user, confirm_negative=False) -> None:
    """Undo a receipt: its ledger entries are reversed (stock returns to
    in-transit) and the receipt is soft-deleted."""
    if receipt.is_deleted:
        raise ValidationError({"receipt": "This receipt is already deleted."})
    before = snapshot_receipt(receipt)

    entries = StockLedgerEntry.objects.filter(
        source_module=MODULE,
        txn_type=TxnType.SHIPMENT_RECEIPT,
        source_id=receipt.pk,
    )
    movements = reversal_movements(entries, notes="Receipt deleted.")

    receipt.is_deleted = True
    receipt.deleted_at = timezone.now()
    receipt.deleted_by = user
    receipt.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])

    if movements:
        post_event(
            txn_type=TxnType.DELETE_REVERSAL,
            source_module=MODULE,
            source_id=receipt.pk,
            movements=movements,
            created_by=user,
            confirm_negative=confirm_negative,
        )
    record_audit(
        action=AuditLog.Action.DELETE,
        module="shipment_receipts",
        record_id=receipt.pk,
        record_repr=str(receipt),
        before=before,
    )


def _unreceived_movements(shipment: Shipment, notes: str) -> list[Movement]:
    """Reversal movements for each line's unreceived in-transit remainder:
    −IN_TRANSIT @ destination, +PHYSICAL back @ source, carrying the exact
    value that is still in transit (§5.2 'reversal of unreceived')."""
    movements = []
    for line in shipment.lines.filter(is_deleted=False):
        sums = StockLedgerEntry.objects.filter(
            source_module=MODULE, source_line_id=line.pk, bucket=Bucket.IN_TRANSIT
        ).aggregate(
            qty=Sum(F("qty_in") - F("qty_out")),
            aed=Sum(
                Case(
                    When(qty_in__gt=0, then=F("aed_value")),
                    default=F("aed_value") * -1,
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                )
            ),
        )
        remaining_qty = sums["qty"] or Decimal("0")
        remaining_aed = sums["aed"] or Decimal("0")
        if remaining_qty <= 0:
            continue
        movements.append(
            Movement(
                product=line.product,
                location=shipment.to_location,
                bucket=Bucket.IN_TRANSIT,
                qty_out=remaining_qty,
                aed_value=max(remaining_aed, Decimal("0")),
                related_location=shipment.from_location,
                source_line_id=line.pk,
                notes=notes,
            )
        )
        movements.append(
            Movement(
                product=line.product,
                location=shipment.from_location,
                bucket=Bucket.PHYSICAL,
                qty_in=remaining_qty,
                aed_value=max(remaining_aed, Decimal("0")),
                related_location=shipment.to_location,
                source_line_id=line.pk,
                notes=notes,
            )
        )
    return movements


@transaction.atomic
def cancel_shipment(*, shipment: Shipment, reason="", user) -> Shipment:
    """Cancel a shipment: unreceived in-transit quantities return to source
    physical stock; already-received stock stays at the destination (§5.2).
    Draft shipments simply become cancelled — nothing was posted."""
    if shipment.is_deleted:
        raise ValidationError({"shipment": "This shipment has been deleted."})
    if shipment.cancelled_at:
        raise ValidationError({"shipment": "This shipment is already cancelled."})
    before = snapshot_shipment(shipment)

    movements = []
    if shipment.shipped_at:
        movements = _unreceived_movements(shipment, notes=f"Shipment cancelled: {reason}"[:255])
        if not movements:
            raise ValidationError(
                {"shipment": "Everything on this shipment was received; nothing to cancel."}
            )

    shipment.cancelled_at = timezone.now()
    shipment.cancel_reason = reason
    shipment.updated_by = user
    shipment.save(update_fields=["cancelled_at", "cancel_reason", "updated_by", "updated_at"])

    if movements:
        post_event(
            txn_type=TxnType.SHIPMENT_CANCEL,
            source_module=MODULE,
            source_id=shipment.pk,
            movements=movements,
            created_by=user,
        )
    record_audit(
        action=AuditLog.Action.UPDATE,
        module=MODULE,
        record_id=shipment.pk,
        record_repr=str(shipment),
        before=before,
        after=snapshot_shipment(shipment),
    )
    return shipment


@transaction.atomic
def soft_delete_shipment(*, shipment: Shipment, user, confirm_negative=False) -> None:
    """Soft delete: every ledger row this shipment ever posted (ship, receipts,
    cancellation) is exactly reversed, returning all moved stock and value to
    the source; receipts and lines are soft-deleted with it (§5.2)."""
    if shipment.is_deleted:
        raise ValidationError({"shipment": "This shipment is already deleted."})
    before = snapshot_shipment(shipment)
    now = timezone.now()

    # Reversing every row the shipment ever posted (ship, receipts, undos,
    # cancellation) nets to an exact undo of its remaining effect: any row
    # already paired with a reversal cancels out inside the set.
    line_ids = list(shipment.lines.values_list("pk", flat=True))
    entries = StockLedgerEntry.objects.filter(
        source_module=MODULE, source_line_id__in=line_ids
    )
    movements = reversal_movements(entries, notes="Shipment deleted.")

    for receipt in shipment.receipts.filter(is_deleted=False):
        receipt.is_deleted, receipt.deleted_at, receipt.deleted_by = True, now, user
        receipt.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])
    for line in shipment.lines.filter(is_deleted=False):
        line.is_deleted, line.deleted_at, line.deleted_by = True, now, user
        line.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])

    if movements:
        post_event(
            txn_type=TxnType.DELETE_REVERSAL,
            source_module=MODULE,
            source_id=shipment.pk,
            movements=movements,
            created_by=user,
            confirm_negative=confirm_negative,
        )

    shipment.is_deleted, shipment.deleted_at, shipment.deleted_by = True, now, user
    shipment.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])
    record_audit(
        action=AuditLog.Action.DELETE,
        module=MODULE,
        record_id=shipment.pk,
        record_repr=str(shipment),
        before=before,
    )


def snapshot_shipment(shipment: Shipment) -> dict:
    return {
        "shipment_no": shipment.shipment_no,
        "shipment_date": str(shipment.shipment_date),
        "from_location": shipment.from_location.name,
        "to_location": shipment.to_location.name,
        "shipment_type": shipment.shipment_type,
        "shipping_cost": str(shipment.shipping_cost),
        "status": shipment.status,
        "notes": shipment.notes,
        "cancel_reason": shipment.cancel_reason,
        "lines": [
            {
                "id": line.pk,
                "product": str(line.product),
                "quantity": str(line.quantity),
                "received_qty": str(line.received_qty),
                "remaining_qty": str(line.remaining_qty),
                "over_received": line.over_received,
                "status": line.status,
                "notes": line.notes,
            }
            for line in shipment.lines.filter(is_deleted=False)
        ],
    }


def snapshot_receipt(receipt: ShipmentReceipt) -> dict:
    return {
        "shipment": receipt.shipment.shipment_no,
        "receipt_date": str(receipt.receipt_date),
        "notes": receipt.notes,
        "lines": [
            {
                "shipment_line": line.shipment_line_id,
                "product": str(line.shipment_line.product),
                "quantity": str(line.quantity),
            }
            for line in receipt.lines.all()
        ],
    }
