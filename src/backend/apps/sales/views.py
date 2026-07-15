from django.db.models import DecimalField, F, Prefetch, Sum
from django.db.models.functions import Coalesce
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError

from apps.accounts.permissions import ModulePermission
from apps.inventory.services import NegativeStockError

from . import services
from .models import Sale, SaleLine
from .serializers import SaleSerializer


def _line_prefetch():
    return Prefetch(
        "lines",
        queryset=SaleLine.objects.filter(is_deleted=False).select_related("product"),
    )


class SaleViewSet(viewsets.ModelViewSet):
    """Sales CRUD (FR-067…FR-072). All stock-affecting writes go through
    apps.sales.services, which post ledger entries and audit rows in the same
    transaction — this viewset never writes ledger state itself."""

    module = "sales"
    permission_classes = [ModulePermission]
    serializer_class = SaleSerializer
    queryset = Sale.objects.filter(is_deleted=False)
    filterset_fields = ["location", "customer", "sale_date"]
    search_fields = ["sale_no", "notes", "lines__product__name", "customer__name"]
    ordering_fields = ["sale_date", "sale_no", "created_at"]

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("location", "customer", "created_by")
            .prefetch_related(_line_prefetch())
        )

    def list(self, request, *args, **kwargs):
        """Standard page plus the quick-totals bar data (FR-103)."""
        response = super().list(request, *args, **kwargs)
        line_agg = SaleLine.objects.filter(
            is_deleted=False, sale__in=self.filter_queryset(self.get_queryset())
        ).aggregate(
            total_quantity=Coalesce(Sum("quantity"), 0, output_field=DecimalField()),
            # Reference only (FR-070): sum of qty × optional price where set.
            total_sale_value=Coalesce(
                Sum(
                    F("quantity") * F("unit_price"),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                ),
                0,
                output_field=DecimalField(),
            ),
        )
        response.data["totals"] = {key: str(value) for key, value in line_agg.items()}
        return response

    def _negative_confirmed(self):
        return self.request.query_params.get("confirm_negative") == "true"

    def perform_create(self, serializer):
        lines = serializer.validated_data.pop("lines")
        try:
            serializer.instance = services.create_sale(
                header=serializer.validated_data,
                lines=lines,
                user=self.request.user,
                confirm_negative=self._negative_confirmed(),
            )
        except NegativeStockError as exc:
            raise ValidationError(
                {"detail": str(exc), "code": "negative_stock_confirmation_required"}
            ) from exc

    def perform_update(self, serializer):
        lines = serializer.validated_data.pop("lines")
        try:
            sale = services.update_sale(
                sale=serializer.instance,
                header=serializer.validated_data,
                lines=lines,
                user=self.request.user,
                confirm_negative=self._negative_confirmed(),
            )
        except NegativeStockError as exc:
            raise ValidationError(
                {"detail": str(exc), "code": "negative_stock_confirmation_required"}
            ) from exc
        # Reload so the response reflects line adds/removes, not the
        # pre-update prefetch cache.
        serializer.instance = self.get_queryset().get(pk=sale.pk)

    def perform_destroy(self, instance):
        services.soft_delete_sale(sale=instance, user=self.request.user)
