"""Sale business services: the only path that writes sales and their ledger
postings.

Every function runs the business-record write, the ledger post, and the audit
row in one ``transaction.atomic()`` block (SRS §7.3). Ledger mapping (§5.2):

- Sale                → −PHYSICAL @ sale location
- Edit of a line      → reversal of the line's net posted state + fresh rows
- Soft delete         → reversal rows only

Stock value leaves at the sale location's carrying average cost from
``stock_balances`` (§5.3.1); the optional sale price is reference-only and
never touches stock value (FR-070). Negative stock on sale requires explicit
confirmation (FR-083).
"""

from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Case, DecimalField, F, Sum, When
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.audits.models import AuditLog
from apps.audits.services import record_audit
from apps.inventory.models import Bucket, StockBalance, StockLedgerEntry, TxnType
from apps.inventory.services import Movement, post_event

from .models import Sale, SaleLine

TWO_PLACES = Decimal("0.01")
MODULE = "sales"


def _money(value) -> Decimal:
    return Decimal(value).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def _validate_header(location) -> None:
    if not location.is_sales_location or not location.is_active:
        raise ValidationError(
            {"location": f"{location.name} is not an active sales location (FR-068)."}
        )


def _validate_lines(lines: list[dict]) -> None:
    if not lines:
        raise ValidationError({"lines": "At least one line is required."})
    for line_data in lines:
        if line_data["quantity"] <= 0:
            raise ValidationError({"quantity": "Sale quantity must be positive."})
        price = line_data.get("unit_price")
        if price is not None and price < 0:
            raise ValidationError({"unit_price": "Sale price cannot be negative."})


class CarryingPool:
    """Running per-product remainder of a location's PHYSICAL balance, so a
    multi-line sale of the same product shares value proportionally and
    empties the pool to exactly zero (same pattern as shipments)."""

    def __init__(self, location):
        self.location = location
        self.pools: dict[int, tuple[Decimal, Decimal]] = {}

    def _load(self, product) -> None:
        if product.pk not in self.pools:
            balance = StockBalance.objects.filter(
                product=product, location=self.location, bucket=Bucket.PHYSICAL
            ).first()
            self.pools[product.pk] = (
                (balance.quantity, balance.value_aed) if balance else (Decimal("0"), Decimal("0"))
            )

    def give(self, product, quantity: Decimal, aed: Decimal) -> None:
        """Credit a reversal back into the pool before fresh rows draw from it."""
        self._load(product)
        pool_qty, pool_aed = self.pools[product.pk]
        self.pools[product.pk] = (pool_qty + quantity, pool_aed + max(aed, Decimal("0")))

    def take(self, product, quantity: Decimal) -> Decimal:
        self._load(product)
        pool_qty, pool_aed = self.pools[product.pk]
        if pool_qty <= 0 or pool_aed <= 0:
            aed = Decimal("0.00")
        elif quantity >= pool_qty:
            aed = pool_aed
        else:
            aed = _money(pool_aed * quantity / pool_qty)
        self.pools[product.pk] = (pool_qty - quantity, pool_aed - aed)
        return aed


def _line_net_posted(line: SaleLine) -> tuple[Decimal, Decimal]:
    """Net (qty, aed) this line has taken out of PHYSICAL per the ledger —
    the amount a reversal must put back."""
    sums = StockLedgerEntry.objects.filter(
        source_module=MODULE, source_line_id=line.pk, bucket=Bucket.PHYSICAL
    ).aggregate(
        qty=Sum(F("qty_out") - F("qty_in")),
        aed=Sum(
            Case(
                When(qty_out__gt=0, then=F("aed_value")),
                default=F("aed_value") * -1,
                output_field=DecimalField(max_digits=14, decimal_places=2),
            )
        ),
    )
    return (sums["qty"] or Decimal("0"), sums["aed"] or Decimal("0"))


def _sale_movement(line: SaleLine, location, aed: Decimal) -> Movement:
    return Movement(
        product=line.product,
        location=location,
        bucket=Bucket.PHYSICAL,
        qty_out=line.quantity,
        aed_value=aed,
        source_line_id=line.pk,
    )


def _reversal_movement(product, line: SaleLine, location, qty: Decimal, aed: Decimal, notes: str):
    return Movement(
        product=product,
        location=location,
        bucket=Bucket.PHYSICAL,
        qty_in=qty,
        aed_value=max(aed, Decimal("0")),
        source_line_id=line.pk,
        notes=notes,
    )


@transaction.atomic
def create_sale(*, header: dict, lines: list[dict], user, confirm_negative=False) -> Sale:
    """Sale entry (FR-072): −PHYSICAL at the sale location, valued at the
    location's carrying average."""
    _validate_header(header["location"])
    _validate_lines(lines)

    sale = Sale.objects.create(created_by=user, updated_by=user, **header)
    if not sale.sale_no:
        sale.sale_no = f"SL-{sale.pk:06d}"
        sale.save(update_fields=["sale_no"])

    pool = CarryingPool(sale.location)
    movements = []
    for line_data in lines:
        line = SaleLine.objects.create(
            sale=sale, created_by=user, updated_by=user, **line_data
        )
        movements.append(
            _sale_movement(line, sale.location, pool.take(line.product, line.quantity))
        )

    post_event(
        txn_type=TxnType.SALE,
        source_module=MODULE,
        source_id=sale.pk,
        movements=movements,
        created_by=user,
        confirm_negative=confirm_negative,
    )
    record_audit(
        action=AuditLog.Action.CREATE,
        module=MODULE,
        record_id=sale.pk,
        record_repr=str(sale),
        after=snapshot_sale(sale),
    )
    return sale


@transaction.atomic
def update_sale(
    *, sale: Sale, header: dict, lines: list[dict], user, confirm_negative=False
) -> Sale:
    """Stock-affecting line edits post reversal rows for the old net state and
    fresh rows at the current carrying average (§5.2, FR-081). The location is
    locked after entry — stock already left it; delete and re-enter to move a
    sale. Price/notes edits post nothing (reference only)."""
    if sale.is_deleted:
        raise ValidationError({"sale": "This sale has been deleted."})
    before = snapshot_sale(sale)

    if "location" in header and header["location"] != sale.location:
        raise ValidationError(
            {"location": "Sale location cannot change after entry; delete and re-enter."}
        )
    for field_name, value in header.items():
        setattr(sale, field_name, value)
    sale.updated_by = user
    sale.save()

    _validate_lines(lines)
    existing = {line.pk: line for line in sale.lines.filter(is_deleted=False)}
    seen = set()
    pool = CarryingPool(sale.location)
    movements = []

    for line_data in lines:
        line_id = line_data.pop("id", None)
        if line_id is None:
            line = SaleLine.objects.create(
                sale=sale, created_by=user, updated_by=user, **line_data
            )
            movements.append(
                _sale_movement(line, sale.location, pool.take(line.product, line.quantity))
            )
            continue

        line = existing.get(line_id)
        if line is None:
            raise ValidationError({"lines": f"Line {line_id} does not belong to this sale."})
        seen.add(line_id)
        old_product = line.product
        stock_changed = (
            old_product != line_data.get("product", old_product)
            or line.quantity != line_data.get("quantity", line.quantity)
        )
        for field_name, value in line_data.items():
            setattr(line, field_name, value)
        line.updated_by = user
        line.save()
        if stock_changed:
            # The reversal restores the *old* product's stock; fresh rows
            # post the new state at the current carrying average.
            net_qty, net_aed = _line_net_posted(line)
            if net_qty > 0:
                movements.append(
                    _reversal_movement(
                        old_product, line, sale.location, net_qty, net_aed,
                        "Edit reversal of prior sale state.",
                    )
                )
                pool.give(old_product, net_qty, net_aed)
            movements.append(
                _sale_movement(line, sale.location, pool.take(line.product, line.quantity))
            )

    now = timezone.now()
    for line in existing.values():
        if line.pk in seen:
            continue
        net_qty, net_aed = _line_net_posted(line)
        if net_qty > 0:
            movements.append(
                _reversal_movement(
                    line.product, line, sale.location, net_qty, net_aed,
                    "Line removed from sale.",
                )
            )
        line.is_deleted, line.deleted_at, line.deleted_by = True, now, user
        line.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])

    if movements:
        post_event(
            txn_type=TxnType.EDIT_REVERSAL,
            source_module=MODULE,
            source_id=sale.pk,
            movements=movements,
            created_by=user,
            confirm_negative=confirm_negative,
        )
    record_audit(
        action=AuditLog.Action.UPDATE,
        module=MODULE,
        record_id=sale.pk,
        record_repr=str(sale),
        before=before,
        after=snapshot_sale(sale),
    )
    return sale


@transaction.atomic
def soft_delete_sale(*, sale: Sale, user) -> None:
    """Soft delete: each line's net sold quantity and value return to the
    location's physical stock (§5.2 reversal rows only)."""
    if sale.is_deleted:
        raise ValidationError({"sale": "This sale is already deleted."})
    before = snapshot_sale(sale)
    now = timezone.now()

    movements = []
    for line in sale.lines.filter(is_deleted=False):
        net_qty, net_aed = _line_net_posted(line)
        if net_qty > 0:
            movements.append(
                _reversal_movement(
                    line.product, line, sale.location, net_qty, net_aed, "Sale deleted."
                )
            )
        line.is_deleted, line.deleted_at, line.deleted_by = True, now, user
        line.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])

    if movements:
        post_event(
            txn_type=TxnType.DELETE_REVERSAL,
            source_module=MODULE,
            source_id=sale.pk,
            movements=movements,
            created_by=user,
        )

    sale.is_deleted, sale.deleted_at, sale.deleted_by = True, now, user
    sale.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])
    record_audit(
        action=AuditLog.Action.DELETE,
        module=MODULE,
        record_id=sale.pk,
        record_repr=str(sale),
        before=before,
    )


def snapshot_sale(sale: Sale) -> dict:
    return {
        "sale_no": sale.sale_no,
        "sale_date": str(sale.sale_date),
        "location": sale.location.name,
        "customer": sale.customer.name,
        "notes": sale.notes,
        "lines": [
            {
                "id": line.pk,
                "product": str(line.product),
                "quantity": str(line.quantity),
                "unit_price": str(line.unit_price) if line.unit_price is not None else None,
                "notes": line.notes,
            }
            for line in sale.lines.filter(is_deleted=False)
        ],
    }
