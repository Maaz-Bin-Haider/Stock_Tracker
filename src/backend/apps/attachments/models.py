from django.conf import settings
from django.db import models

from apps.core.models import CompanyScopedModel


class FileAttachment(CompanyScopedModel):
    """Uploaded invoice/bill file linked to a business record (FR-104…FR-107).

    The database stores metadata and the storage key only, never file bytes
    (FR-105); files live in Django's default storage — local media in
    development, S3-compatible storage in deployment.
    """

    module = models.CharField(max_length=32)  # "purchases" | "sales"
    record_id = models.BigIntegerField()
    file = models.FileField(upload_to="uploads/%Y/%m/")
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=64)
    size = models.BigIntegerField()
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="attachments"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-uploaded_at", "-id"]
        indexes = [models.Index(fields=["module", "record_id"])]

    def __str__(self):
        return f"{self.original_name} ({self.module}#{self.record_id})"
