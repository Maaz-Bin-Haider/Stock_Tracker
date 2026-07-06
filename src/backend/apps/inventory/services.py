"""The stock posting service — the only writer of ledger rows.

Every stock-changing business event calls ``post_event`` inside the same
database transaction as its business-record writes, so partial updates are
impossible (SRS §7.3, TECHNICAL_ARCHITECTURE §5.4). Balance rows are locked
with SELECT ... FOR UPDATE so concurrent movements of the same
product+location+bucket serialize.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import Bucket, StockBalance, StockLedgerEntry

TWO_PLACES = Decimal("0.01")


class PostingError(Exception):
    """Invalid movement passed to post_event; nothing is written."""


class NegativeStockError(PostingError):
    """PHYSICAL stock would go negative and the caller did not confirm.

    The API surfaces this as a warning requiring explicit user confirmation
    (FR-082/FR-083); passing ``confirm_negative=True`` allows the post.
    """

    def __init__(self, product, location, resulting_qty):
        self.product = product
        self.location = location
        self.resulting_qty = resulting_qty
        super().__init__(
            f"Stock of {product} at {location} would become {resulting_qty}. "
            "Explicit confirmation is required for negative stock."
        )


@dataclass(frozen=True)
class Movement:
    """One ledger row: a quantity moving in or out of a bucket at a location.

    ``aed_value``/``gst_value`` are magnitudes; direction follows the quantity
    (qty_in adds value to the balance, qty_out removes it).
    """

    product: object
    location: object
    bucket: str
    qty_in: Decimal = Decimal("0")
    qty_out: Decimal = Decimal("0")
    aed_value: Decimal = Decimal("0")
    gst_value: Decimal = Decimal("0")
    currency: str = ""
    related_location: object = None
    source_line_id: int | None = None
    reversal_of: StockLedgerEntry | None = None
    notes: str = ""

    def __post_init__(self):
        if (self.qty_in <= 0) == (self.qty_out <= 0):
            raise PostingError("Movement needs exactly one of qty_in/qty_out > 0.")
        if self.qty_in < 0 or self.qty_out < 0 or self.aed_value < 0 or self.gst_value < 0:
            raise PostingError("Movement quantities and values must be magnitudes >= 0.")
        if self.bucket not in Bucket.values:
            raise PostingError(f"Unknown stock bucket {self.bucket!r}.")


@dataclass(frozen=True)
class PostedEvent:
    entries: list[StockLedgerEntry] = field(default_factory=list)


def post_event(
    *,
    txn_type,
    source_module,
    source_id,
    movements,
    txn_at=None,
    created_by=None,
    confirm_negative=False,
) -> PostedEvent:
    """Append ledger rows for one business event and roll balances forward.

    Must be called inside the caller's ``transaction.atomic()`` block together
    with the business-record write and its audit entry. ``atomic`` here is a
    no-op savepoint-free guard when already inside a transaction.
    """
    movements = list(movements)
    if not movements:
        raise PostingError("post_event called with no movements.")
    txn_at = txn_at or timezone.now()

    with transaction.atomic():
        entries = []
        for move in movements:
            balance, _created = (
                StockBalance.objects.select_for_update().get_or_create(
                    product=move.product, location=move.location, bucket=move.bucket
                )
            )
            net_qty = move.qty_in - move.qty_out
            net_value = move.aed_value if move.qty_in else -move.aed_value
            balance.quantity += net_qty
            balance.value_aed += net_value
            if (
                move.bucket == Bucket.PHYSICAL
                and move.qty_out
                and balance.quantity < 0
                and not confirm_negative
            ):
                raise NegativeStockError(move.product, move.location, balance.quantity)
            balance.save(update_fields=["quantity", "value_aed", "updated_at"])

            entries.append(
                StockLedgerEntry(
                    txn_at=txn_at,
                    txn_type=txn_type,
                    source_module=source_module,
                    source_id=source_id,
                    source_line_id=move.source_line_id,
                    reversal_of=move.reversal_of,
                    product=move.product,
                    location=move.location,
                    bucket=move.bucket,
                    qty_in=move.qty_in.quantize(TWO_PLACES),
                    qty_out=move.qty_out.quantize(TWO_PLACES),
                    related_location=move.related_location,
                    currency=move.currency,
                    aed_value=move.aed_value.quantize(TWO_PLACES),
                    gst_value=move.gst_value.quantize(TWO_PLACES),
                    notes=move.notes,
                    created_by=created_by,
                )
            )
        StockLedgerEntry.objects.bulk_create(entries)
    return PostedEvent(entries=entries)


def reversal_movements(entries, notes=""):
    """Build Movements that exactly undo the given ledger entries (§5.2).

    Used by edit/delete flows: reversal rows reference the originals so
    history is never destroyed (SRS §8.2/§8.3).
    """
    moves = []
    for entry in entries:
        moves.append(
            Movement(
                product=entry.product,
                location=entry.location,
                bucket=entry.bucket,
                qty_in=entry.qty_out,
                qty_out=entry.qty_in,
                aed_value=entry.aed_value,
                gst_value=entry.gst_value,
                currency=entry.currency,
                related_location=entry.related_location,
                source_line_id=entry.source_line_id,
                reversal_of=entry,
                notes=notes,
            )
        )
    return moves


def rebuild_stock_balances():
    """Recompute every StockBalance from the full ledger; report drift.

    The consistency check behind TECHNICAL_ARCHITECTURE §5.3: any service that
    forgets a ledger row (or a balance update) shows up as drift here.
    Returns a list of human-readable drift strings (empty = clean).
    """
    from django.db.models import Case, DecimalField, F, Sum, When

    computed = {}
    rows = (
        StockLedgerEntry.objects.values("product_id", "location_id", "bucket")
        .annotate(
            quantity=Sum(F("qty_in") - F("qty_out")),
            value_aed=Sum(
                Case(
                    When(qty_in__gt=0, then=F("aed_value")),
                    default=F("aed_value") * -1,
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                )
            ),
        )
    )
    for row in rows:
        key = (row["product_id"], row["location_id"], row["bucket"])
        computed[key] = (row["quantity"], row["value_aed"])

    drift = []
    with transaction.atomic():
        balances = StockBalance.objects.select_for_update().all()
        seen = set()
        for balance in balances:
            key = (balance.product_id, balance.location_id, balance.bucket)
            seen.add(key)
            quantity, value_aed = computed.get(key, (Decimal("0"), Decimal("0")))
            if balance.quantity != quantity or balance.value_aed != value_aed:
                drift.append(
                    f"{balance.product_id}/{balance.location_id}/{balance.bucket}: "
                    f"balance {balance.quantity}@{balance.value_aed} "
                    f"!= ledger {quantity}@{value_aed}"
                )
                balance.quantity = quantity
                balance.value_aed = value_aed
                balance.save(update_fields=["quantity", "value_aed", "updated_at"])
        for key, (quantity, value_aed) in computed.items():
            if key in seen:
                continue
            product_id, location_id, bucket = key
            drift.append(f"{product_id}/{location_id}/{bucket}: missing balance row, created")
            StockBalance.objects.create(
                product_id=product_id,
                location_id=location_id,
                bucket=bucket,
                quantity=quantity,
                value_aed=value_aed,
            )
    return drift
