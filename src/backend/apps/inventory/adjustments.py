"""Stock adjustment services (FR-074…FR-077): manual ±PHYSICAL corrections.

Separate from ``services.py`` so the posting service stays narrow. Ledger
mapping (§5.2): adjustment → ±PHYSICAL @ location; edits → reversal of the
net posted state + fresh rows; soft delete → reversal rows only. Value moves
at the location's carrying average (§5.3.1): decreases take a proportional
share of the balance pool (exact when it empties), increases add at the
current average so the unit cost is undisturbed.
"""

from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Case, DecimalField, F, Sum, When
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.audits.models import AuditLog
from apps.audits.services import record_audit

from .models import AdjustmentType, Bucket, StockAdjustment, StockBalance, StockLedgerEntry, TxnType
from .services import Movement, post_event

TWO_PLACES = Decimal("0.01")
MODULE = "stock_adjustments"


def _money(value) -> Decimal:
    return Decimal(value).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def _carrying_share(product, location, quantity: Decimal, *, adding: bool) -> Decimal:
    """AED moved with ``quantity`` at the location's carrying average.

    Decreases empty the pool exactly (all remaining value moves with the last
    unit); increases never take more than the average — they extend the pool
    at its current unit cost.
    """
    balance = StockBalance.objects.filter(
        product=product, location=location, bucket=Bucket.PHYSICAL
    ).first()
    if balance is None or balance.quantity <= 0 or balance.value_aed <= 0:
        return Decimal("0.00")
    if not adding and quantity >= balance.quantity:
        return balance.value_aed
    return _money(balance.value_aed * quantity / balance.quantity)


def _net_posted(adjustment: StockAdjustment) -> tuple[Decimal, Decimal]:
    """Net (qty, aed) into PHYSICAL this adjustment has posted (signed)."""
    sums = StockLedgerEntry.objects.filter(
        source_module=MODULE, source_id=adjustment.pk, bucket=Bucket.PHYSICAL
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
    return (sums["qty"] or Decimal("0"), sums["aed"] or Decimal("0"))


def _adjustment_movement(adjustment: StockAdjustment) -> Movement:
    increase = adjustment.adjustment_type == AdjustmentType.INCREASE
    aed = _carrying_share(
        adjustment.product, adjustment.location, adjustment.quantity, adding=increase
    )
    return Movement(
        product=adjustment.product,
        location=adjustment.location,
        bucket=Bucket.PHYSICAL,
        qty_in=adjustment.quantity if increase else Decimal("0"),
        qty_out=Decimal("0") if increase else adjustment.quantity,
        aed_value=aed,
        notes=f"Adjustment: {adjustment.reason}"[:255],
    )


def _reverse_net_movement(adjustment: StockAdjustment, notes: str) -> Movement | None:
    net_qty, net_aed = _net_posted(adjustment)
    if net_qty == 0:
        return None
    return Movement(
        product=adjustment.product,
        location=adjustment.location,
        bucket=Bucket.PHYSICAL,
        qty_in=-net_qty if net_qty < 0 else Decimal("0"),
        qty_out=net_qty if net_qty > 0 else Decimal("0"),
        aed_value=max(abs(net_aed), Decimal("0")),
        notes=notes,
    )


def _validate(data: dict) -> None:
    if data.get("quantity") is not None and data["quantity"] <= 0:
        raise ValidationError({"quantity": "Adjustment quantity must be positive."})
    if "reason" in data and not str(data["reason"]).strip():
        raise ValidationError({"reason": "A reason is required (FR-075)."})


@transaction.atomic
def create_adjustment(*, data: dict, user, confirm_negative=False) -> StockAdjustment:
    _validate(data)
    adjustment = StockAdjustment.objects.create(created_by=user, updated_by=user, **data)
    post_event(
        txn_type=TxnType.ADJUSTMENT,
        source_module=MODULE,
        source_id=adjustment.pk,
        movements=[_adjustment_movement(adjustment)],
        created_by=user,
        confirm_negative=confirm_negative,
    )
    record_audit(
        action=AuditLog.Action.CREATE,
        module=MODULE,
        record_id=adjustment.pk,
        record_repr=str(adjustment),
        after=snapshot_adjustment(adjustment),
    )
    return adjustment


@transaction.atomic
def update_adjustment(
    *, adjustment: StockAdjustment, data: dict, user, confirm_negative=False
) -> StockAdjustment:
    """Reversal of the net posted state + fresh rows for the new (§5.2)."""
    if adjustment.is_deleted:
        raise ValidationError({"adjustment": "This adjustment has been deleted."})
    _validate(data)
    before = snapshot_adjustment(adjustment)

    stock_fields = ("location", "product", "adjustment_type", "quantity")
    stock_changed = any(
        field in data and getattr(adjustment, field) != data[field] for field in stock_fields
    )
    reversal = _reverse_net_movement(adjustment, "Edit reversal of prior adjustment.")

    for field_name, value in data.items():
        setattr(adjustment, field_name, value)
    adjustment.updated_by = user
    adjustment.save()

    if stock_changed:
        movements = [move for move in (reversal, _adjustment_movement(adjustment)) if move]
        post_event(
            txn_type=TxnType.EDIT_REVERSAL,
            source_module=MODULE,
            source_id=adjustment.pk,
            movements=movements,
            created_by=user,
            confirm_negative=confirm_negative,
        )
    record_audit(
        action=AuditLog.Action.UPDATE,
        module=MODULE,
        record_id=adjustment.pk,
        record_repr=str(adjustment),
        before=before,
        after=snapshot_adjustment(adjustment),
    )
    return adjustment


@transaction.atomic
def soft_delete_adjustment(
    *, adjustment: StockAdjustment, user, confirm_negative=False
) -> None:
    if adjustment.is_deleted:
        raise ValidationError({"adjustment": "This adjustment is already deleted."})
    before = snapshot_adjustment(adjustment)

    reversal = _reverse_net_movement(adjustment, "Adjustment deleted.")
    adjustment.is_deleted = True
    adjustment.deleted_at = timezone.now()
    adjustment.deleted_by = user
    adjustment.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])

    if reversal:
        post_event(
            txn_type=TxnType.DELETE_REVERSAL,
            source_module=MODULE,
            source_id=adjustment.pk,
            movements=[reversal],
            created_by=user,
            confirm_negative=confirm_negative,
        )
    record_audit(
        action=AuditLog.Action.DELETE,
        module=MODULE,
        record_id=adjustment.pk,
        record_repr=str(adjustment),
        before=before,
    )


def snapshot_adjustment(adjustment: StockAdjustment) -> dict:
    return {
        "adjustment_date": str(adjustment.adjustment_date),
        "location": adjustment.location.name,
        "product": str(adjustment.product),
        "adjustment_type": adjustment.adjustment_type,
        "quantity": str(adjustment.quantity),
        "reason": adjustment.reason,
        "notes": adjustment.notes,
    }
