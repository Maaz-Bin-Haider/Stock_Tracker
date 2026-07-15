from rest_framework import serializers

from .models import StockAdjustment, StockBalance, StockLedgerEntry


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


class StockAdjustmentSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.__str__", read_only=True)
    location_name = serializers.CharField(source="location.name", read_only=True)
    created_by_username = serializers.CharField(
        source="created_by.username", read_only=True, default=None
    )

    class Meta:
        model = StockAdjustment
        fields = [
            "id",
            "adjustment_date",
            "location",
            "location_name",
            "product",
            "product_name",
            "adjustment_type",
            "quantity",
            "reason",
            "notes",
            "created_by_username",
            "created_at",
        ]

    def validate(self, attrs):
        quantity = attrs.get("quantity", getattr(self.instance, "quantity", None))
        if quantity is not None and quantity <= 0:
            raise serializers.ValidationError({"quantity": "Quantity must be positive."})
        reason = attrs.get("reason", getattr(self.instance, "reason", ""))
        if not reason.strip():
            raise serializers.ValidationError({"reason": "A reason is required (FR-075)."})
        return attrs


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
