from rest_framework import viewsets

from apps.accounts.models import User

from .models import StockBalance, StockLedgerEntry
from .serializers import StockBalanceSerializer, StockLedgerEntrySerializer


class StockLedgerViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only ledger view (FR-078/FR-113): everyone sees all movements.

    Rows are append-only; no API mutates them.
    """

    queryset = StockLedgerEntry.objects.select_related(
        "product", "location", "related_location", "created_by"
    )
    serializer_class = StockLedgerEntrySerializer
    filterset_fields = ["product", "location", "bucket", "txn_type", "source_module"]
    search_fields = ["product__name", "notes", "source_module"]
    ordering_fields = ["txn_at", "id"]


class StockBalanceViewSet(viewsets.ReadOnlyModelViewSet):
    """Current stock per product/location/bucket, derived from the ledger.

    ``value_aed`` is stock valuation data and admin-only (FR-116) — it is
    stripped server-side for other roles, not just hidden in the UI.
    """

    queryset = StockBalance.objects.select_related("product", "location")
    serializer_class = StockBalanceSerializer
    filterset_fields = ["product", "location", "bucket"]
    search_fields = ["product__name", "location__name"]
    ordering_fields = ["quantity", "updated_at"]

    def get_serializer(self, *args, **kwargs):
        serializer = super().get_serializer(*args, **kwargs)
        user = self.request.user
        if not (user.is_authenticated and user.role == User.Role.ADMIN):
            child = getattr(serializer, "child", serializer)
            child.fields.pop("value_aed", None)
        return serializer
