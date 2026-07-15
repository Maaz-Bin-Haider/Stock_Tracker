from django.db.models import DecimalField, Prefetch, Sum
from django.db.models.functions import Coalesce
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.accounts.permissions import ModulePermission
from apps.inventory.services import NegativeStockError

from . import services
from .models import (
    Shipment,
    ShipmentLine,
    ShipmentReceipt,
    annotate_shipment_line_quantities,
)
from .serializers import ShipmentReceiptSerializer, ShipmentSerializer


def _line_prefetch():
    return Prefetch(
        "lines",
        queryset=annotate_shipment_line_quantities(
            ShipmentLine.objects.filter(is_deleted=False).select_related("product")
        ),
    )


class ShipmentViewSet(viewsets.ModelViewSet):
    """Shipments plus explicit ship/receive/cancel sub-actions (§6: status
    transitions get their own endpoints, never bare PATCHes).

    All stock-affecting writes go through apps.shipments.services, which post
    ledger entries and audit rows in the same transaction.
    """

    module = "shipments"
    permission_classes = [ModulePermission]
    serializer_class = ShipmentSerializer
    queryset = Shipment.objects.filter(is_deleted=False)
    filterset_fields = ["from_location", "to_location", "shipment_type", "shipment_date"]
    search_fields = ["shipment_no", "notes", "lines__product__name"]
    ordering_fields = ["shipment_date", "shipment_no", "created_at"]

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("from_location", "to_location", "created_by")
            .prefetch_related(_line_prefetch())
        )

    def list(self, request, *args, **kwargs):
        """Standard page plus the quick-totals bar data (FR-103)."""
        response = super().list(request, *args, **kwargs)
        line_agg = annotate_shipment_line_quantities(
            ShipmentLine.objects.filter(
                is_deleted=False, shipment__in=self.filter_queryset(self.get_queryset())
            )
        ).aggregate(
            total_shipped=Coalesce(Sum("quantity"), 0, output_field=DecimalField()),
            total_received=Coalesce(Sum("received_qty_agg"), 0, output_field=DecimalField()),
            total_remaining=Coalesce(Sum("remaining_qty_agg"), 0, output_field=DecimalField()),
        )
        response.data["totals"] = {key: str(value) for key, value in line_agg.items()}
        return response

    def _negative_confirmed(self):
        return self.request.query_params.get("confirm_negative") == "true"

    def perform_create(self, serializer):
        lines = serializer.validated_data.pop("lines")
        ship = serializer.validated_data.pop("ship", False)
        try:
            serializer.instance = services.create_shipment(
                header=serializer.validated_data,
                lines=lines,
                ship=ship,
                user=self.request.user,
                confirm_negative=self._negative_confirmed(),
            )
        except NegativeStockError as exc:
            raise ValidationError(
                {"detail": str(exc), "code": "negative_stock_confirmation_required"}
            ) from exc

    def perform_update(self, serializer):
        lines = serializer.validated_data.pop("lines")
        serializer.validated_data.pop("ship", None)
        shipment = services.update_shipment(
            shipment=serializer.instance,
            header=serializer.validated_data,
            lines=lines,
            user=self.request.user,
        )
        # Reload so the response reflects line adds/removes, not the
        # pre-update prefetch cache.
        serializer.instance = self.get_queryset().get(pk=shipment.pk)

    def perform_destroy(self, instance):
        try:
            services.soft_delete_shipment(
                shipment=instance,
                user=self.request.user,
                confirm_negative=self._negative_confirmed(),
            )
        except NegativeStockError as exc:
            raise ValidationError(
                {"detail": str(exc), "code": "negative_stock_confirmation_required"}
            ) from exc

    @action(detail=True, methods=["post"], url_path="ship")
    def ship(self, request, pk=None):
        """Mark shipped: posts −PHYSICAL @ source / +IN_TRANSIT @ destination
        at the source's carrying average cost (FR-063, §5.3.1)."""
        shipment = self.get_object()
        try:
            services.ship_shipment(
                shipment=shipment,
                user=request.user,
                confirm_negative=self._negative_confirmed(),
            )
        except NegativeStockError as exc:
            raise ValidationError(
                {"detail": str(exc), "code": "negative_stock_confirmation_required"}
            ) from exc
        return Response(self.get_serializer(self.get_object()).data)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        """Cancel: unreceived in-transit stock returns to the source;
        received stock stays at the destination (§5.2)."""
        shipment = self.get_object()
        services.cancel_shipment(
            shipment=shipment, reason=request.data.get("reason", ""), user=request.user
        )
        return Response(self.get_serializer(self.get_object()).data)

    @action(detail=True, methods=["get", "post"], url_path="receipts")
    def receipts(self, request, pk=None):
        """Receiving sub-resource (FR-061/FR-064): partial and over-receiving
        per product line, with the over_received flag driving warnings."""
        shipment = self.get_object()
        if request.method == "GET":
            queryset = shipment.receipts.filter(is_deleted=False).prefetch_related(
                "lines__shipment_line__product"
            )
            return Response(ShipmentReceiptSerializer(queryset, many=True).data)

        serializer = ShipmentReceiptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        receipt = services.receive_shipment(
            shipment=shipment,
            receipt_date=serializer.validated_data["receipt_date"],
            lines=serializer.validated_data["lines"],
            notes=serializer.validated_data.get("notes", ""),
            user=request.user,
        )
        return Response(
            ShipmentReceiptSerializer(receipt).data, status=status.HTTP_201_CREATED
        )

    @action(
        detail=True,
        methods=["delete"],
        url_path="receipts/(?P<receipt_pk>[0-9]+)",
    )
    def delete_receipt(self, request, pk=None, receipt_pk=None):
        shipment = self.get_object()
        try:
            receipt = shipment.receipts.get(pk=receipt_pk, is_deleted=False)
        except ShipmentReceipt.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        try:
            services.delete_receipt(
                receipt=receipt,
                user=request.user,
                confirm_negative=self._negative_confirmed(),
            )
        except NegativeStockError as exc:
            raise ValidationError(
                {"detail": str(exc), "code": "negative_stock_confirmation_required"}
            ) from exc
        return Response(status=status.HTTP_204_NO_CONTENT)
