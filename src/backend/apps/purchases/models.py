from decimal import Decimal

from django.db import models
from django.db.models import Sum

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

    def _agg(self, attr: str, fallback) -> Decimal:
        annotated = getattr(self, f"{attr}_agg", None)
        return annotated if annotated is not None else fallback()

    @property
    def collected_qty(self) -> Decimal:
        return self._agg(
            "collected_qty",
            lambda: self.collection_lines.filter(collection__is_deleted=False).aggregate(
                total=Sum("quantity")
            )["total"]
            or ZERO,
        )

    def _refund_sum(self, source: str) -> Decimal:
        return (
            self.refund_lines.filter(refund__is_deleted=False, source=source).aggregate(
                total=Sum("quantity")
            )["total"]
            or ZERO
        )

    @property
    def cancelled_pending_qty(self) -> Decimal:
        """Undelivered quantity cancelled/refunded (FR-049)."""
        return self._agg(
            "cancelled_pending_qty", lambda: self._refund_sum(RefundSource.PENDING)
        )

    @property
    def refunded_received_qty(self) -> Decimal:
        """Delivered quantity returned to the supplier (FR-050)."""
        return self._agg(
            "refunded_received_qty", lambda: self._refund_sum(RefundSource.RECEIVED)
        )

    @property
    def refunded_qty(self) -> Decimal:
        return self.cancelled_pending_qty + self.refunded_received_qty

    @property
    def pending_qty(self) -> Decimal:
        """SYSTEM_SPEC §8: purchased − collected − cancelled/refunded pending."""
        return self.quantity - self.collected_qty - self.cancelled_pending_qty

    @property
    def net_qty(self) -> Decimal:
        """Net after refund/cancellation — the GST report quantity (SRS §5.1)."""
        return self.quantity - self.refunded_qty

    @property
    def status(self) -> str:
        collected = self.collected_qty
        refunded = self.refunded_qty
        if refunded >= self.quantity:
            return (
                PurchaseStatus.REFUNDED
                if self.refunded_received_qty > 0
                else PurchaseStatus.CANCELLED
            )
        if self.pending_qty <= 0 and collected > 0:
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


class RefundSource(models.TextChoices):
    """Which bucket a refund/cancellation quantity comes out of.

    PENDING cancels undelivered quantity (FR-049); RECEIVED returns delivered
    stock and reverses physical stock (FR-050).
    """

    PENDING = "PENDING", "Pending (cancel undelivered)"
    RECEIVED = "RECEIVED", "Received (return delivered stock)"


class PurchaseRefund(TimeStampedModel, CompanyScopedModel, SoftDeleteModel):
    """One refund/cancellation event against a purchase (FR-044…FR-054).

    Creates reversal ledger entries; the original purchase stays untouched
    and traceable (SRS §8.2/§8.3).
    """

    purchase = models.ForeignKey(Purchase, on_delete=models.PROTECT, related_name="refunds")
    refund_no = models.CharField(max_length=64, blank=True, db_index=True)
    refund_date = models.DateField()
    reason = models.TextField()
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-refund_date", "-id"]

    def __str__(self):
        return f"Refund {self.refund_no or self.pk} for {self.purchase.invoice_no}"


class PurchaseRefundLine(CompanyScopedModel):
    """Reversal amounts are frozen at refund time, at the original purchase
    line rate (FR-054/FR-093/FR-122), for the GST and refund reports."""

    refund = models.ForeignKey(PurchaseRefund, on_delete=models.PROTECT, related_name="lines")
    purchase_line = models.ForeignKey(
        PurchaseLine, on_delete=models.PROTECT, related_name="refund_lines"
    )
    source = models.CharField(max_length=16, choices=RefundSource.choices)
    quantity = models.DecimalField(max_digits=14, decimal_places=2)
    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="+",
        help_text="For RECEIVED refunds: where the returned stock leaves physical stock.",
    )
    value_reversal = models.DecimalField(
        max_digits=14, decimal_places=2, default=ZERO, help_text="In the line's currency."
    )
    value_reversal_aed = models.DecimalField(max_digits=14, decimal_places=2, default=ZERO)
    gst_reversal = models.DecimalField(
        max_digits=14, decimal_places=2, default=ZERO, help_text="In the line's currency."
    )
    gst_reversal_aed = models.DecimalField(max_digits=14, decimal_places=2, default=ZERO)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"Refund {self.quantity} ({self.source}) of {self.purchase_line.product}"


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


def _sum_subquery(queryset):
    """SUM(quantity) as a subquery — immune to the join fan-out that plain
    multi-relation Sum annotations produce."""
    from django.db.models import DecimalField, OuterRef, Subquery
    from django.db.models.functions import Coalesce

    return Coalesce(
        Subquery(
            queryset.filter(purchase_line=OuterRef("pk"))
            .values("purchase_line")
            .annotate(total=Sum("quantity"))
            .values("total")
        ),
        ZERO,
        output_field=DecimalField(max_digits=14, decimal_places=2),
    )


def annotate_line_quantities(queryset):
    """Attach collected/refunded/pending sums for list-page performance
    (TECHNICAL_ARCHITECTURE §4: computed quantities as annotated querysets)."""
    from django.db.models import F

    return queryset.annotate(
        collected_qty_agg=_sum_subquery(
            PurchaseCollectionLine.objects.filter(collection__is_deleted=False)
        ),
        cancelled_pending_qty_agg=_sum_subquery(
            PurchaseRefundLine.objects.filter(
                refund__is_deleted=False, source=RefundSource.PENDING
            )
        ),
        refunded_received_qty_agg=_sum_subquery(
            PurchaseRefundLine.objects.filter(
                refund__is_deleted=False, source=RefundSource.RECEIVED
            )
        ),
    ).annotate(
        pending_qty_agg=F("quantity") - F("collected_qty_agg") - F("cancelled_pending_qty_agg"),
    )
