"""Report, dashboard, valuation, and export endpoints.

Reads are open to every authenticated user (SYSTEM_SPEC §6: view + export
reports for all roles) except the admin-only valuation reports (FR-116),
which are enforced here and again in the export pipeline — never just hidden
in the UI. Report data itself is built by apps.reports.builders.
"""

from django.conf import settings
from django.db import transaction
from django.http import FileResponse
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User

from .builders import REPORTS, visible_reports
from .dashboard import dashboard_data
from .filters import parse_filters
from .models import ExportJob
from .serializers import ExportJobSerializer
from .tasks import run_export

# Server-side cap for the interactive JSON view; exports always contain the
# full filtered dataset.
MAX_ROWS = 2000


def _is_admin(user) -> bool:
    return user.role == User.Role.ADMIN


def _get_report(key: str, user):
    report = REPORTS.get(key)
    if report is None:
        raise NotFound(f"Unknown report {key!r}.")
    if report.admin_only and not _is_admin(user):
        raise PermissionDenied("Stock valuation is available to admin users only.")
    return report


class DashboardView(APIView):
    """Live dashboard cards, or a past snapshot with ?cutoff= (FR-094…FR-096)."""

    def get(self, request):
        filters = parse_filters(request.query_params)
        return Response(dashboard_data(cutoff=filters.get("cutoff")))


class ReportIndexView(APIView):
    """The report catalogue the UI renders its picker from."""

    def get(self, request):
        return Response(
            [
                {
                    "key": report.key,
                    "title": report.title,
                    "description": report.description,
                    "filters": report.filters,
                    "admin_only": report.admin_only,
                }
                for report in visible_reports(_is_admin(request.user))
            ]
        )


class ReportDataView(APIView):
    """One report's full filtered dataset (capped for the interactive view)."""

    def get(self, request, key):
        report = _get_report(key, request.user)
        filters = parse_filters(request.query_params)
        result = report.build(filters, _is_admin(request.user))

        sections = []
        truncated = False
        for section in result.sections:
            rows = section.rows
            if len(rows) > MAX_ROWS:
                rows = rows[:MAX_ROWS]
                truncated = True
            sections.append(
                {
                    "title": section.title,
                    "columns": [
                        {"key": column.key, "label": column.label, "kind": column.kind}
                        for column in section.columns
                    ],
                    "rows": rows,
                    "row_count": len(section.rows),
                }
            )
        return Response(
            {
                "key": report.key,
                "title": report.title,
                "sections": sections,
                "totals": result.totals,
                "truncated": truncated,
            }
        )


class ExportCreateView(APIView):
    """Validate filters, enqueue the Celery export, return the job (FR-098)."""

    def post(self, request, key):
        report = _get_report(key, request.user)
        format_value = str(request.data.get("format", "")).upper()
        if format_value not in ExportJob.Format.values:
            raise ValidationError({"format": "Use 'XLSX' or 'PDF'."})

        raw_filters = request.data.get("filters") or {}
        if not isinstance(raw_filters, dict):
            raise ValidationError({"filters": "Expected an object of filter values."})
        parse_filters(raw_filters)  # validate now; the task re-parses the same params

        job = ExportJob.objects.create(
            report_key=report.key,
            params={key: str(value) for key, value in raw_filters.items() if value},
            format=format_value,
            created_by=request.user,
        )
        if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
            run_export(job.pk)
            job.refresh_from_db()
        else:
            transaction.on_commit(lambda: run_export.delay(job.pk))
        return Response(ExportJobSerializer(job).data, status=201)


class ExportJobViewSet(viewsets.ReadOnlyModelViewSet):
    """Poll/list/download export jobs. Users see their own jobs; admins all."""

    serializer_class = ExportJobSerializer

    def get_queryset(self):
        jobs = ExportJob.objects.select_related("created_by")
        if not _is_admin(self.request.user):
            jobs = jobs.filter(created_by=self.request.user)
        return jobs

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        job = self.get_object()
        if job.status != ExportJob.Status.DONE or not job.file:
            raise ValidationError({"detail": f"Export is {job.status}, not ready to download."})
        content_type = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            if job.format == ExportJob.Format.XLSX
            else "application/pdf"
        )
        return FileResponse(
            job.file.open("rb"),
            as_attachment=True,
            filename=job.file.name.rsplit("/", 1)[-1],
            content_type=content_type,
        )
