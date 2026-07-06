from django.conf import settings
from django.db import models

from apps.core.models import CompanyScopedModel
from apps.masterdata.models import Location
from apps.products.models import Product


class Bucket(models.TextChoices):
    """The three stock buckets per product/location (SRS §1.4, CLAUDE.md)."""

    PHYSICAL = "PHYSICAL", "Physical"
    PENDING = "PENDING", "Pending"
    IN_TRANSIT = "IN_TRANSIT", "In transit"


class TxnType(models.TextChoices):
    """Business events that post ledger entries (TECHNICAL_ARCHITECTURE §5.2)."""

    PURCHASE_ENTRY = "PURCHASE_ENTRY", "Purchase line entered"
    PURCHASE_COLLECTION = "PURCHASE_COLLECTION", "Purchase collection"
    PURCHASE_REFUND = "PURCHASE_REFUND", "Purchase refund/cancellation"
    SHIPMENT_OUT = "SHIPMENT_OUT", "Shipment shipped"
    SHIPMENT_RECEIPT = "SHIPMENT_RECEIPT", "Shipment receipt"
    SHIPMENT_CANCEL = "SHIPMENT_CANCEL", "Shipment cancelled"
    SALE = "SALE", "Sale"
    ADJUSTMENT = "ADJUSTMENT", "Stock adjustment"
    EDIT_REVERSAL = "EDIT_REVERSAL", "Edit reversal"
    DELETE_REVERSAL = "DELETE_REVERSAL", "Delete reversal"


class StockLedgerEntry(CompanyScopedModel):
    """Append-only source of truth for all stock movement (SRS §8.1, FR-078).

    Rows are never updated or deleted — corrections are new reversal rows
    referencing the original via ``reversal_of``.
    """

    txn_at = models.DateTimeField(db_index=True)
    txn_type = models.CharField(max_length=32, choices=TxnType.choices)
    source_module = models.CharField(max_length=64)
    source_id = models.BigIntegerField()
    source_line_id = models.BigIntegerField(null=True, blank=True)
    reversal_of = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="reversals"
    )
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="ledger_entries")
    location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name="ledger_entries")
    bucket = models.CharField(max_length=16, choices=Bucket.choices)
    qty_in = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    qty_out = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    related_location = models.ForeignKey(
        Location, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    currency = models.CharField(max_length=8, blank=True)
    aed_value = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        help_text="AED value magnitude moved with this row; qty_in adds it, qty_out removes it.",
    )
    gst_value = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        help_text="GST magnitude in AED where relevant; same direction convention as aed_value.",
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-txn_at", "-id"]
        indexes = [
            models.Index(fields=["product", "location", "bucket"]),
            models.Index(fields=["source_module", "source_id"]),
            models.Index(fields=["txn_type", "txn_at"]),
        ]
        verbose_name_plural = "stock ledger entries"

    def __str__(self):
        sign = "+" if self.qty_in else "-"
        qty = self.qty_in or self.qty_out
        return f"{self.txn_type} {sign}{qty} {self.bucket} {self.product} @ {self.location}"

    @property
    def net_qty(self):
        return self.qty_in - self.qty_out


class StockBalance(CompanyScopedModel):
    """Materialized rollup of the ledger (TECHNICAL_ARCHITECTURE §5.3).

    Updated in the same transaction as ledger inserts under row locks; the
    ledger stays the source of truth and ``rebuild_stock_balances`` reconciles.
    ``value_aed / quantity`` is the weighted average unit cost (§5.3.1).
    """

    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="stock_balances")
    location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name="stock_balances")
    bucket = models.CharField(max_length=16, choices=Bucket.choices)
    quantity = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    value_aed = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["product_id", "location_id", "bucket"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "location", "bucket"], name="uniq_stock_balance"
            ),
        ]
        indexes = [models.Index(fields=["location", "bucket"])]

    def __str__(self):
        return f"{self.product} @ {self.location} [{self.bucket}]: {self.quantity}"
