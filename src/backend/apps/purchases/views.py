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
    Purchase,
    PurchaseCollection,
    PurchaseLine,
    PurchaseRefund,
    annotate_line_quantities,
)
from .serializers import (
    PurchaseCollectionSerializer,
    PurchaseLineSerializer,
    PurchaseRefundSerializer,
    PurchaseSerializer,
)


def _line_prefetch():
    return Prefetch(
        "lines",
        queryset=annotate_line_quantities(
            PurchaseLine.objects.filter(is_deleted=False).select_related("product", "currency")
        ),
    )


class PurchaseViewSet(viewsets.ModelViewSet):
    """Purchase invoices plus their explicit collection sub-resource.

    All stock-affecting writes go through apps.purchases.services, which post
    ledger entries and audit rows in the same transaction — this viewset never
    writes ledger state itself.
    """

    module = "purchases"
    permission_classes = [ModulePermission]
    serializer_class = PurchaseSerializer
    queryset = Purchase.objects.filter(is_deleted=False)
    filterset_fields = ["location", "supplier", "purchase_date"]
    search_fields = ["invoice_no", "notes", "lines__product__name", "supplier__name"]
    ordering_fields = ["purchase_date", "invoice_no", "created_at"]

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("location", "supplier", "created_by")
            .prefetch_related(_line_prefetch())
        )

    def list(self, request, *args, **kwargs):
        """Standard page plus the quick-totals bar data (FR-103)."""
        response = super().list(request, *args, **kwargs)
        line_agg = annotate_line_quantities(
            PurchaseLine.objects.filter(
                is_deleted=False, purchase__in=self.filter_queryset(self.get_queryset())
            )
        ).aggregate(
            total_quantity=Coalesce(Sum("quantity"), 0, output_field=DecimalField()),
            total_pending=Coalesce(Sum("pending_qty_agg"), 0, output_field=DecimalField()),
            total_collected=Coalesce(Sum("collected_qty_agg"), 0, output_field=DecimalField()),
            total_value_aed=Coalesce(Sum("total_value_aed"), 0, output_field=DecimalField()),
            total_gst_aed=Coalesce(Sum("gst_amount_aed"), 0, output_field=DecimalField()),
        )
        response.data["totals"] = {key: str(value) for key, value in line_agg.items()}
        return response

    def perform_create(self, serializer):
        lines = serializer.validated_data.pop("lines")
        serializer.instance = services.create_purchase(
            header=serializer.validated_data, lines=lines, user=self.request.user
        )

    def perform_update(self, serializer):
        lines = serializer.validated_data.pop("lines")
        serializer.instance = services.update_purchase(
            purchase=serializer.instance,
            header=serializer.validated_data,
            lines=lines,
            user=self.request.user,
        )

    def perform_destroy(self, instance):
        confirm = self.request.query_params.get("confirm_negative") == "true"
        try:
            services.soft_delete_purchase(
                purchase=instance, user=self.request.user, confirm_negative=confirm
            )
        except NegativeStockError as exc:
            raise ValidationError(
                {"detail": str(exc), "code": "negative_stock_confirmation_required"}
            ) from exc

    @action(detail=True, methods=["get", "post"], url_path="collections")
    def collections(self, request, pk=None):
        purchase = self.get_object()
        if request.method == "GET":
            queryset = purchase.collections.filter(is_deleted=False).select_related(
                "location", "created_by"
            )
            return Response(PurchaseCollectionSerializer(queryset, many=True).data)

        serializer = PurchaseCollectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        collection = services.collect_purchase(
            purchase=purchase,
            collection_date=serializer.validated_data["collection_date"],
            location=serializer.validated_data.get("location", purchase.location),
            lines=serializer.validated_data["lines"],
            notes=serializer.validated_data.get("notes", ""),
            user=request.user,
        )
        return Response(
            PurchaseCollectionSerializer(collection).data, status=status.HTTP_201_CREATED
        )

    @action(
        detail=True,
        methods=["delete"],
        url_path="collections/(?P<collection_pk>[0-9]+)",
    )
    def delete_collection(self, request, pk=None, collection_pk=None):
        purchase = self.get_object()
        try:
            collection = purchase.collections.get(pk=collection_pk, is_deleted=False)
        except PurchaseCollection.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        confirm = request.query_params.get("confirm_negative") == "true"
        try:
            services.delete_collection(
                collection=collection, user=request.user, confirm_negative=confirm
            )
        except NegativeStockError as exc:
            raise ValidationError(
                {"detail": str(exc), "code": "negative_stock_confirmation_required"}
            ) from exc
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get", "post"], url_path="refunds")
    def refunds(self, request, pk=None):
        """Refund/cancellation sub-resource (FR-044…FR-054): reversal entries
        against a selected invoice, never edits to the original."""
        purchase = self.get_object()
        if request.method == "GET":
            queryset = purchase.refunds.filter(is_deleted=False).prefetch_related(
                "lines__purchase_line__product", "lines__location"
            )
            return Response(PurchaseRefundSerializer(queryset, many=True).data)

        serializer = PurchaseRefundSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        confirm = request.query_params.get("confirm_negative") == "true"
        try:
            refund = services.create_refund(
                purchase=purchase,
                refund_date=serializer.validated_data["refund_date"],
                reason=serializer.validated_data["reason"],
                lines=serializer.validated_data["lines"],
                notes=serializer.validated_data.get("notes", ""),
                user=request.user,
                confirm_negative=confirm,
            )
        except NegativeStockError as exc:
            raise ValidationError(
                {"detail": str(exc), "code": "negative_stock_confirmation_required"}
            ) from exc
        return Response(PurchaseRefundSerializer(refund).data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["delete"],
        url_path="refunds/(?P<refund_pk>[0-9]+)",
    )
    def delete_refund(self, request, pk=None, refund_pk=None):
        purchase = self.get_object()
        try:
            refund = purchase.refunds.get(pk=refund_pk, is_deleted=False)
        except PurchaseRefund.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        confirm = request.query_params.get("confirm_negative") == "true"
        try:
            services.delete_refund(refund=refund, user=request.user, confirm_negative=confirm)
        except NegativeStockError as exc:
            raise ValidationError(
                {"detail": str(exc), "code": "negative_stock_confirmation_required"}
            ) from exc
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], url_path="pending-lines")
    def pending_lines(self, request):
        """Purchase Collection/Pending page feed (FR-043): every line that
        still has uncollected quantity, with invoice context."""
        lines = (
            annotate_line_quantities(
                PurchaseLine.objects.filter(is_deleted=False, purchase__is_deleted=False)
            )
            .filter(pending_qty_agg__gt=0)
            .select_related("purchase__location", "purchase__supplier", "product", "currency")
            .order_by("purchase__purchase_date", "purchase_id", "id")
        )
        location = request.query_params.get("location")
        if location:
            lines = lines.filter(purchase__location_id=location)
        product = request.query_params.get("product")
        if product:
            lines = lines.filter(product_id=product)

        page = self.paginate_queryset(lines)
        data = [
            {
                **PurchaseLineSerializer(line).data,
                "purchase": line.purchase_id,
                "invoice_no": line.purchase.invoice_no,
                "purchase_date": line.purchase.purchase_date,
                "location": line.purchase.location_id,
                "location_name": line.purchase.location.name,
                "supplier_name": line.purchase.supplier.name,
            }
            for line in (page if page is not None else lines)
        ]
        if page is not None:
            return self.get_paginated_response(data)
        return Response(data)
