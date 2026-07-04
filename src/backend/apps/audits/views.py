from rest_framework import viewsets

from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Audit Activity is visible to all authenticated users (FR-113); read-only."""

    queryset = AuditLog.objects.select_related("user")
    serializer_class = AuditLogSerializer
    filterset_fields = ["action", "module", "user", "record_id"]
    search_fields = ["record_repr", "module", "user__username"]
    ordering_fields = ["created_at"]
