from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import models

from apps.core.models import CompanyScopedModel


def exports_storage():
    """Private storage for generated report files (FR-105): local directory
    outside MEDIA_ROOT in development (nginx serves /media publicly, exports
    must only flow through the authenticated download endpoint — FR-116),
    S3-compatible storage in deployment via configuration."""
    return FileSystemStorage(location=settings.EXPORTS_ROOT)


class ExportJob(CompanyScopedModel):
    """One queued report export (FR-098…FR-101).

    The Celery worker re-runs the report with the stored params, so the file
    contains exactly the filtered dataset the user requested — never more.
    """

    class Format(models.TextChoices):
        XLSX = "XLSX", "Excel"
        PDF = "PDF", "PDF"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        RUNNING = "RUNNING", "Running"
        DONE = "DONE", "Done"
        FAILED = "FAILED", "Failed"

    report_key = models.CharField(max_length=64)
    params = models.JSONField(default=dict, blank=True)
    format = models.CharField(max_length=8, choices=Format.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    file = models.FileField(storage=exports_storage, upload_to="%Y/%m/", blank=True)
    error = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="export_jobs"
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.report_key} {self.format} ({self.status})"
