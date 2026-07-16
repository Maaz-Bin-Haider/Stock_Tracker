from rest_framework import serializers

from .builders import REPORTS
from .models import ExportJob


class ExportJobSerializer(serializers.ModelSerializer):
    report_title = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)

    class Meta:
        model = ExportJob
        fields = [
            "id",
            "report_key",
            "report_title",
            "params",
            "format",
            "status",
            "error",
            "created_by_username",
            "created_at",
            "finished_at",
            "download_url",
        ]

    def get_report_title(self, job):
        report = REPORTS.get(job.report_key)
        return report.title if report else job.report_key

    def get_download_url(self, job):
        if job.status != ExportJob.Status.DONE:
            return None
        return f"/api/v1/reports/exports/{job.pk}/download/"
