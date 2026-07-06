from rest_framework import serializers

from .models import StockBalance, StockLedgerEntry


class StockLedgerEntrySerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.__str__", read_only=True)
    location_name = serializers.CharField(source="location.name", read_only=True)
    related_location_name = serializers.CharField(
        source="related_location.name", read_only=True, default=None
    )
    created_by_username = serializers.CharField(
        source="created_by.username", read_only=True, default=None
    )
    net_qty = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = StockLedgerEntry
        fields = [
            "id",
            "txn_at",
            "txn_type",
            "source_module",
            "source_id",
            "source_line_id",
            "reversal_of",
            "product",
            "product_name",
            "location",
            "location_name",
            "bucket",
            "qty_in",
            "qty_out",
            "net_qty",
            "related_location",
            "related_location_name",
            "currency",
            "aed_value",
            "gst_value",
            "notes",
            "created_by",
            "created_by_username",
            "created_at",
        ]


class StockBalanceSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.__str__", read_only=True)
    location_name = serializers.CharField(source="location.name", read_only=True)

    class Meta:
        model = StockBalance
        fields = [
            "id",
            "product",
            "product_name",
            "location",
            "location_name",
            "bucket",
            "quantity",
            "value_aed",
            "updated_at",
        ]
