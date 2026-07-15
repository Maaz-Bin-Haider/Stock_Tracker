from rest_framework import viewsets
from rest_framework.exceptions import ValidationError

from apps.accounts.models import User
from apps.accounts.permissions import ModulePermission

from . import adjustments
from .models import StockAdjustment, StockBalance, StockLedgerEntry
from .serializers import (
    StockAdjustmentSerializer,
    StockBalanceSerializer,
    StockLedgerEntrySerializer,
)
from .services import NegativeStockError


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


class StockAdjustmentViewSet(viewsets.ModelViewSet):
    """Manual stock corrections (FR-074…FR-077): admin-only writes per the
    SYSTEM_SPEC §6 matrix; every write posts ledger + audit via the
    adjustment services."""

    module = "stock_adjustments"
    permission_classes = [ModulePermission]
    serializer_class = StockAdjustmentSerializer
    queryset = StockAdjustment.objects.filter(is_deleted=False).select_related(
        "product", "location", "created_by"
    )
    filterset_fields = ["location", "product", "adjustment_type", "adjustment_date"]
    search_fields = ["reason", "notes", "product__name"]
    ordering_fields = ["adjustment_date", "created_at"]

    def _negative_confirmed(self):
        return self.request.query_params.get("confirm_negative") == "true"

    def _run(self, func, **kwargs):
        try:
            return func(
                user=self.request.user, confirm_negative=self._negative_confirmed(), **kwargs
            )
        except NegativeStockError as exc:
            raise ValidationError(
                {"detail": str(exc), "code": "negative_stock_confirmation_required"}
            ) from exc

    def perform_create(self, serializer):
        serializer.instance = self._run(
            adjustments.create_adjustment, data=serializer.validated_data
        )

    def perform_update(self, serializer):
        serializer.instance = self._run(
            adjustments.update_adjustment,
            adjustment=serializer.instance,
            data=serializer.validated_data,
        )

    def perform_destroy(self, instance):
        self._run(adjustments.soft_delete_adjustment, adjustment=instance)


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
