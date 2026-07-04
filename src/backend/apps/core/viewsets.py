from rest_framework import viewsets

from apps.accounts.permissions import ModulePermission
from apps.audits.models import AuditLog
from apps.audits.services import record_audit


class AuditedModelViewSet(viewsets.ModelViewSet):
    """Base CRUD viewset: enforces the role matrix and audits every write.

    Subclasses set ``module`` (the ROLE_MATRIX key) and the usual
    queryset/serializer_class. Models are expected to carry the
    TimeStampedModel columns.
    """

    module = ""
    permission_classes = [ModulePermission]

    def _snapshot(self, instance):
        return self.get_serializer(instance).data

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user, updated_by=self.request.user)
        record_audit(
            action=AuditLog.Action.CREATE,
            module=self.module,
            record_id=instance.pk,
            record_repr=str(instance),
            after=self._snapshot(instance),
        )

    def perform_update(self, serializer):
        before = self._snapshot(serializer.instance)
        instance = serializer.save(updated_by=self.request.user)
        record_audit(
            action=AuditLog.Action.UPDATE,
            module=self.module,
            record_id=instance.pk,
            record_repr=str(instance),
            before=before,
            after=self._snapshot(instance),
        )

    def perform_destroy(self, instance):
        before = self._snapshot(instance)
        record_id, record_repr = instance.pk, str(instance)
        instance.delete()
        record_audit(
            action=AuditLog.Action.DELETE,
            module=self.module,
            record_id=record_id,
            record_repr=record_repr,
            before=before,
        )
