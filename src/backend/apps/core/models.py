from django.conf import settings
from django.db import models


class TimeStampedModel(models.Model):
    """created/updated audit columns required on every business table (SRS §6.2)."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )

    class Meta:
        abstract = True


class CompanyScopedModel(models.Model):
    """Nullable company scope for future multi-company support (SRS §6.2)."""

    company_id = models.BigIntegerField(null=True, blank=True, db_index=True)

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    """Stock-affecting records are never physically deleted (SYSTEM_SPEC §25)."""

    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )

    class Meta:
        abstract = True
