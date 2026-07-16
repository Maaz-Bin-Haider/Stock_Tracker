"""Celery export pipeline (TECHNICAL_ARCHITECTURE §8): the endpoint validates
and enqueues, this task renders and stores the file, the UI polls/downloads."""

from celery import shared_task
from django.core.files.base import ContentFile
from django.utils import timezone

from apps.accounts.models import User
from apps.core.time import business_tz


@shared_task
def run_export(job_id: int):
    from .builders import REPORTS
    from .filters import describe_filters, parse_filters
    from .models import ExportJob
    from .rendering import render_pdf, render_xlsx

    job = ExportJob.objects.get(pk=job_id)
    job.status = ExportJob.Status.RUNNING
    job.save(update_fields=["status"])

    try:
        report = REPORTS[job.report_key]
        # Admin-only datasets stay admin-only in files too (FR-116/FR-123):
        # the builder sees the requester's role, exactly like the JSON view.
        is_admin = job.created_by.role == User.Role.ADMIN
        filters = parse_filters(job.params)
        result = report.build(filters, is_admin)

        now = timezone.now().astimezone(business_tz())
        generated = (
            f"Generated {now.strftime('%d/%m/%Y %H:%M')} (Dubai time) "
            f"by {job.created_by.username}"
        )
        if job.format == ExportJob.Format.XLSX:
            content = render_xlsx(report.title, generated, describe_filters(filters), result)
            extension = "xlsx"
        else:
            content = render_pdf(report.title, generated, describe_filters(filters), result)
            extension = "pdf"

        filename = f"{job.report_key}-{now.strftime('%Y%m%d-%H%M%S')}-{job.pk}.{extension}"
        job.file.save(filename, ContentFile(content), save=False)
        job.status = ExportJob.Status.DONE
    except Exception as exc:  # noqa: BLE001 — status must reflect any failure
        job.status = ExportJob.Status.FAILED
        job.error = str(exc)[:2000]
    job.finished_at = timezone.now()
    job.save()
    return job.status
