from decimal import Decimal

from django.db import models
from django.db.models import Sum

from apps.core.models import CompanyScopedModel, SoftDeleteModel, TimeStampedModel
from apps.masterdata.models import Location
from apps.products.models import Product

ZERO = Decimal("0.00")


class ShipmentType(models.TextChoices):
    """FR-058/FR-065: the Dubai→Karachi transfer is its own flow, tracked by
    type; ledger behavior is identical (stock moves between locations)."""

    STANDARD = "STANDARD", "Standard shipment"
    DUBAI_KARACHI = "DUBAI_KARACHI", "Dubai → Karachi transfer"


class ShipmentStatus(models.TextChoices):
    """Computed from shipped/cancelled facts and receipt quantities, never
    stored user input (FR-060, SYSTEM_SPEC §8)."""

    DRAFT = "DRAFT", "Draft"
    SHIPPED = "SHIPPED", "Shipped"
    PARTIALLY_RECEIVED = "PARTIALLY_RECEIVED", "Partially received"
    FULLY_RECEIVED = "FULLY_RECEIVED", "Fully received"
    CANCELLED = "CANCELLED", "Cancelled"


class Shipment(TimeStampedModel, CompanyScopedModel, SoftDeleteModel):
    """Shipment header (FR-058). Shipping cost is recorded here but never
    enters stock value (FR-119); shipments carry no currency (FR-066).

    ``shipped_at``/``cancelled_at`` record events (set by the ship/cancel
    services, which post the ledger rows); status is derived from them.
    """

    shipment_no = models.CharField(max_length=64, blank=True, db_index=True)
    shipment_date = models.DateField(db_index=True)
    from_location = models.ForeignKey(
        Location, on_delete=models.PROTECT, related_name="shipments_out"
    )
    to_location = models.ForeignKey(
        Location, on_delete=models.PROTECT, related_name="shipments_in"
    )
    shipment_type = models.CharField(
        max_length=32, choices=ShipmentType.choices, default=ShipmentType.STANDARD
    )
    shipping_cost = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=ZERO,
        help_text="Recorded for reference in AED terms; excluded from stock value (FR-119).",
    )
    notes = models.TextField(blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancel_reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-shipment_date", "-id"]
        indexes = [
            models.Index(fields=["from_location", "shipment_date"]),
            models.Index(fields=["to_location", "shipment_date"]),
        ]

    def __str__(self):
        return f"Shipment {self.shipment_no or self.pk}"

    @property
    def status(self) -> str:
        if self.cancelled_at:
            return ShipmentStatus.CANCELLED
        if not self.shipped_at:
            return ShipmentStatus.DRAFT
        lines = [line for line in self.lines.all() if not line.is_deleted]
        if lines and all(line.received_qty >= line.quantity for line in lines):
            return ShipmentStatus.FULLY_RECEIVED
        if any(line.received_qty > 0 for line in lines):
            return ShipmentStatus.PARTIALLY_RECEIVED
        return ShipmentStatus.SHIPPED


class ShipmentLine(TimeStampedModel, CompanyScopedModel, SoftDeleteModel):
    """One product on a shipment (FR-059). Received/remaining quantities and
    the over_received flag are always computed from receipt lines."""

    shipment = models.ForeignKey(Shipment, on_delete=models.PROTECT, related_name="lines")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="shipment_lines")
    quantity = models.DecimalField(max_digits=14, decimal_places=2)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["id"]
        indexes = [models.Index(fields=["product"])]

    def __str__(self):
        return f"{self.shipment}: {self.quantity} x {self.product}"

    @property
    def received_qty(self) -> Decimal:
        annotated = getattr(self, "received_qty_agg", None)
        if annotated is not None:
            return annotated
        return (
            self.receipt_lines.filter(receipt__is_deleted=False).aggregate(
                total=Sum("quantity")
            )["total"]
            or ZERO
        )

    @property
    def remaining_qty(self) -> Decimal:
        """Still expected (may be negative when over-received, FR-084)."""
        return self.quantity - self.received_qty

    @property
    def over_received(self) -> bool:
        """Drives the warning highlight (§5.2 note, FR-085)."""
        return self.received_qty > self.quantity

    @property
    def status(self) -> str:
        if self.shipment.cancelled_at:
            return ShipmentStatus.CANCELLED
        if not self.shipment.shipped_at:
            return ShipmentStatus.DRAFT
        received = self.received_qty
        if received >= self.quantity:
            return ShipmentStatus.FULLY_RECEIVED
        if received > 0:
            return ShipmentStatus.PARTIALLY_RECEIVED
        return ShipmentStatus.SHIPPED


class ShipmentReceipt(TimeStampedModel, CompanyScopedModel, SoftDeleteModel):
    """One receiving event against a shipment (FR-061/FR-062): −IN_TRANSIT,
    +PHYSICAL at the destination via the ledger."""

    shipment = models.ForeignKey(Shipment, on_delete=models.PROTECT, related_name="receipts")
    receipt_date = models.DateField()
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-receipt_date", "-id"]

    def __str__(self):
        return f"Receipt #{self.pk} for {self.shipment}"


class ShipmentReceiptLine(CompanyScopedModel):
    receipt = models.ForeignKey(ShipmentReceipt, on_delete=models.PROTECT, related_name="lines")
    shipment_line = models.ForeignKey(
        ShipmentLine, on_delete=models.PROTECT, related_name="receipt_lines"
    )
    quantity = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"Receive {self.quantity} of {self.shipment_line.product}"


def annotate_shipment_line_quantities(queryset):
    """Attach received sums for list-page performance, mirroring
    purchases.annotate_line_quantities (subquery — no join fan-out)."""
    from django.db.models import DecimalField, F, OuterRef, Subquery
    from django.db.models.functions import Coalesce

    received = Coalesce(
        Subquery(
            ShipmentReceiptLine.objects.filter(
                receipt__is_deleted=False, shipment_line=OuterRef("pk")
            )
            .values("shipment_line")
            .annotate(total=Sum("quantity"))
            .values("total")
        ),
        ZERO,
        output_field=DecimalField(max_digits=14, decimal_places=2),
    )
    return queryset.annotate(received_qty_agg=received).annotate(
        remaining_qty_agg=F("quantity") - F("received_qty_agg")
    )
