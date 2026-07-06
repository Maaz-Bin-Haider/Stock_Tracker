from decimal import Decimal

from django.db import models
from django.db.models import Q, Sum

from apps.core.models import CompanyScopedModel, SoftDeleteModel, TimeStampedModel
from apps.masterdata.models import Currency, GstRate, Location, Supplier
from apps.products.models import Product

ZERO = Decimal("0.00")


class PurchaseStatus(models.TextChoices):
    """Computed from line quantities, never stored user input (SYSTEM_SPEC §8)."""

    PENDING = "PENDING", "Pending"
    PARTIALLY_RECEIVED = "PARTIALLY_RECEIVED", "Partially received"
    FULLY_COLLECTED = "FULLY_COLLECTED", "Fully collected"
    CANCELLED = "CANCELLED", "Cancelled"
    REFUNDED = "REFUNDED", "Refunded"


class Purchase(TimeStampedModel, CompanyScopedModel, SoftDeleteModel):
    """Purchase invoice header (FR-032). One invoice, many product lines."""

    invoice_no = models.CharField(max_length=64, db_index=True)
    purchase_date = models.DateField(db_index=True)
    location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name="purchases")
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="purchases")
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-purchase_date", "-id"]
        indexes = [
            models.Index(fields=["supplier", "purchase_date"]),
            models.Index(fields=["location", "purchase_date"]),
        ]

    def __str__(self):
        return f"Purchase {self.invoice_no}"

    @property
    def status(self) -> str:
        lines = [line for line in self.lines.all() if not line.is_deleted]
        if not lines:
            return PurchaseStatus.PENDING
        statuses = {line.status for line in lines}
        if statuses <= {PurchaseStatus.CANCELLED, PurchaseStatus.REFUNDED}:
            return statuses.pop() if len(statuses) == 1 else PurchaseStatus.CANCELLED
        if statuses <= {
            PurchaseStatus.FULLY_COLLECTED,
            PurchaseStatus.CANCELLED,
            PurchaseStatus.REFUNDED,
        }:
            return PurchaseStatus.FULLY_COLLECTED
        if any(line.collected_qty > 0 for line in lines):
            return PurchaseStatus.PARTIALLY_RECEIVED
        return PurchaseStatus.PENDING


class PurchaseLine(TimeStampedModel, CompanyScopedModel, SoftDeleteModel):
    """One product line: money values frozen at entry time so history never
    drifts when settings change (TECHNICAL_ARCHITECTURE §4, ADR 7).

    Collected/refunded/pending quantities and status are always computed from
    collection/refund lines — never stored user input.
    """

    purchase = models.ForeignKey(Purchase, on_delete=models.PROTECT, related_name="lines")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="purchase_lines")
    quantity = models.DecimalField(max_digits=14, decimal_places=2)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name="+")
    exchange_rate = models.DecimalField(
        max_digits=12, decimal_places=6, help_text="Rate to AED frozen at entry (FR-089)."
    )
    unit_price_aed = models.DecimalField(max_digits=14, decimal_places=2)
    total_value_aed = models.DecimalField(max_digits=14, decimal_places=2)
    gst_rate = models.ForeignKey(
        GstRate, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    gst_rate_percent = models.DecimalField(max_digits=5, decimal_places=2, default=ZERO)
    gst_amount = models.DecimalField(
        max_digits=14, decimal_places=2, default=ZERO, help_text="In the line's currency."
    )
    gst_amount_aed = models.DecimalField(max_digits=14, decimal_places=2, default=ZERO)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["id"]
        indexes = [models.Index(fields=["product"])]

    def __str__(self):
        return f"{self.purchase.invoice_no}: {self.quantity} x {self.product}"

    @property
    def collected_qty(self) -> Decimal:
        aggregate = self.collection_lines.filter(
            collection__is_deleted=False,
        ).aggregate(total=Sum("quantity"))
        return aggregate["total"] or ZERO

    @property
    def refunded_qty(self) -> Decimal:
        # Refund lines arrive in M3; the pending formula already accounts for them.
        return ZERO

    @property
    def pending_qty(self) -> Decimal:
        return self.quantity - self.collected_qty - self.refunded_qty

    @property
    def status(self) -> str:
        collected = self.collected_qty
        if self.pending_qty <= 0 and collected >= self.quantity:
            return PurchaseStatus.FULLY_COLLECTED
        if collected > 0:
            return PurchaseStatus.PARTIALLY_RECEIVED
        return PurchaseStatus.PENDING


class PurchaseCollection(TimeStampedModel, CompanyScopedModel, SoftDeleteModel):
    """One collection event against a purchase (FR-039…FR-043). Collection
    increases physical stock at the collection location via the ledger."""

    purchase = models.ForeignKey(Purchase, on_delete=models.PROTECT, related_name="collections")
    collection_date = models.DateField()
    location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name="+")
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-collection_date", "-id"]

    def __str__(self):
        return f"Collection #{self.pk} for {self.purchase.invoice_no}"


class PurchaseCollectionLine(CompanyScopedModel):
    collection = models.ForeignKey(
        PurchaseCollection, on_delete=models.PROTECT, related_name="lines"
    )
    purchase_line = models.ForeignKey(
        PurchaseLine, on_delete=models.PROTECT, related_name="collection_lines"
    )
    quantity = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"Collect {self.quantity} of {self.purchase_line.product}"


def annotate_line_quantities(queryset):
    """Attach collected/pending sums for list-page performance
    (TECHNICAL_ARCHITECTURE §4: computed quantities as annotated querysets)."""
    from django.db.models import DecimalField, F
    from django.db.models.functions import Coalesce

    return queryset.annotate(
        collected_qty_agg=Coalesce(
            Sum(
                "collection_lines__quantity",
                filter=Q(collection_lines__collection__is_deleted=False),
            ),
            ZERO,
            output_field=DecimalField(max_digits=14, decimal_places=2),
        ),
    ).annotate(pending_qty_agg=F("quantity") - F("collected_qty_agg"))
