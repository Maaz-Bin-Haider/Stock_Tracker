from django.db import models
from django.db.models.functions import Lower

from apps.core.models import CompanyScopedModel, TimeStampedModel
from apps.masterdata.models import Category


class Product(TimeStampedModel, CompanyScopedModel):
    sku = models.CharField(max_length=64, blank=True)
    name = models.CharField(max_length=255)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    brand = models.CharField(max_length=128, blank=True)
    model = models.CharField(max_length=128, blank=True)
    storage_specs = models.CharField(max_length=128, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name", "storage_specs"]
        constraints = [
            # FR-018/FR-019: exact duplicates blocked case-insensitively; the
            # same name with different storage/specs is allowed.
            models.UniqueConstraint(
                Lower("name"),
                Lower("storage_specs"),
                name="uniq_product_name_specs_ci",
            ),
        ]

    def __str__(self):
        return f"{self.name} {self.storage_specs}".strip()
