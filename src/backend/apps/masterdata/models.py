from django.db import models

from apps.core.models import CompanyScopedModel, TimeStampedModel


class Category(TimeStampedModel, CompanyScopedModel):
    name = models.CharField(max_length=128, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Location(TimeStampedModel, CompanyScopedModel):
    """Behavior flags instead of hardcoded names (TECHNICAL_ARCHITECTURE §4)."""

    name = models.CharField(max_length=128, unique=True)
    country = models.CharField(max_length=64, blank=True)
    city = models.CharField(max_length=64, blank=True)
    can_purchase = models.BooleanField(default=True)
    is_sales_location = models.BooleanField(default=False)
    region_group = models.CharField(
        max_length=32,
        blank=True,
        help_text="Reporting group, e.g. AU for the calculated combined-Australia view.",
    )
    gst_region = models.CharField(
        max_length=32,
        blank=True,
        help_text="Non-empty when purchases at this location attract GST (e.g. AU, NZ).",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Currency(TimeStampedModel, CompanyScopedModel):
    code = models.CharField(max_length=8, unique=True)
    name = models.CharField(max_length=64, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]
        verbose_name_plural = "currencies"

    def __str__(self):
        return self.code


class ExchangeRate(TimeStampedModel, CompanyScopedModel):
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name="rates")
    rate_to_aed = models.DecimalField(max_digits=12, decimal_places=6)
    effective_date = models.DateField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-effective_date"]
        indexes = [models.Index(fields=["currency", "effective_date"])]

    def __str__(self):
        return f"{self.currency.code} {self.rate_to_aed} ({self.effective_date})"


class GstRate(TimeStampedModel, CompanyScopedModel):
    location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name="gst_rates")
    rate = models.DecimalField(max_digits=5, decimal_places=2, help_text="Percent, e.g. 10.00")
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["location__name", "-effective_from"]
        indexes = [models.Index(fields=["location", "effective_from"])]

    def __str__(self):
        return f"{self.location.name} {self.rate}%"


class Supplier(TimeStampedModel, CompanyScopedModel):
    code = models.CharField(max_length=32, blank=True)
    name = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=128, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)
    country = models.CharField(max_length=64, blank=True)
    city = models.CharField(max_length=64, blank=True)
    address = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Customer(TimeStampedModel, CompanyScopedModel):
    code = models.CharField(max_length=32, blank=True)
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)
    country = models.CharField(max_length=64, blank=True)
    city = models.CharField(max_length=64, blank=True)
    address = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
