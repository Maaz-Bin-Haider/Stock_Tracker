from django.http import FileResponse
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied

from apps.accounts.permissions import ROLE_MATRIX
from apps.audits.models import AuditLog
from apps.audits.services import record_audit

from .models import FileAttachment
from .serializers import FileAttachmentSerializer


class FileAttachmentViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Invoice/bill uploads (FR-104…FR-107).

    Reads are open to every authenticated user (all users view all data,
    FR-106); uploading or deleting a file requires write access to the module
    the file belongs to, per the SYSTEM_SPEC §6 matrix — a sale user cannot
    attach files to purchases and vice versa.
    """

    queryset = FileAttachment.objects.select_related("uploaded_by")
    serializer_class = FileAttachmentSerializer
    filterset_fields = ["module", "record_id"]
    search_fields = ["original_name"]

    def _check_write(self, module):
        if self.request.user.role not in ROLE_MATRIX.get(module, frozenset()):
            raise PermissionDenied(f"Your role cannot manage {module} files.")

    def perform_create(self, serializer):
        self._check_write(serializer.validated_data["module"])
        attachment = serializer.save(uploaded_by=self.request.user)
        # FR-107: upload activity lands in the audit trail.
        record_audit(
            action=AuditLog.Action.CREATE,
            module="attachments",
            record_id=attachment.pk,
            record_repr=str(attachment),
            after={
                "module": attachment.module,
                "record_id": attachment.record_id,
                "file": attachment.original_name,
                "content_type": attachment.content_type,
                "size": attachment.size,
            },
        )

    def perform_destroy(self, instance):
        self._check_write(instance.module)
        before = {
            "module": instance.module,
            "record_id": instance.record_id,
            "file": instance.original_name,
        }
        record_id, record_repr = instance.pk, str(instance)
        instance.file.delete(save=False)
        instance.delete()
        record_audit(
            action=AuditLog.Action.DELETE,
            module="attachments",
            record_id=record_id,
            record_repr=record_repr,
            before=before,
        )

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        attachment = self.get_object()
        return FileResponse(
            attachment.file.open("rb"),
            as_attachment=True,
            filename=attachment.original_name,
            content_type=attachment.content_type,
        )
