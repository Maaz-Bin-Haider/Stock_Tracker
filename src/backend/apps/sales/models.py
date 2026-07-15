from decimal import Decimal

from django.db import models

from apps.core.models import CompanyScopedModel, SoftDeleteModel, TimeStampedModel
from apps.masterdata.models import Customer, Location
from apps.products.models import Product

ZERO = Decimal("0.00")


class Sale(TimeStampedModel, CompanyScopedModel, SoftDeleteModel):
    """Sale header (FR-069): only sales locations (Dubai, Karachi) may sell
    (FR-068); customers are tracked; there is no payment status (FR-071)."""

    sale_no = models.CharField(max_length=64, blank=True, db_index=True)
    sale_date = models.DateField(db_index=True)
    location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name="sales")
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="sales")
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-sale_date", "-id"]
        indexes = [
            models.Index(fields=["customer", "sale_date"]),
            models.Index(fields=["location", "sale_date"]),
        ]

    def __str__(self):
        return f"Sale {self.sale_no or self.pk}"


class SaleLine(TimeStampedModel, CompanyScopedModel, SoftDeleteModel):
    """One product sold. ``unit_price`` is optional and reference-only — it
    is never used for stock value or profit (FR-070, SRS §8.4); stock value
    leaves at the location's carrying average via the ledger."""

    sale = models.ForeignKey(Sale, on_delete=models.PROTECT, related_name="lines")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="sale_lines")
    quantity = models.DecimalField(max_digits=14, decimal_places=2)
    unit_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Optional reference-only sale price (FR-070); no currency handling.",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["id"]
        indexes = [models.Index(fields=["product"])]

    def __str__(self):
        return f"{self.sale}: {self.quantity} x {self.product}"
