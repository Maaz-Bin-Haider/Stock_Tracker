from rest_framework import serializers

from .models import Shipment, ShipmentLine, ShipmentReceipt


class ShipmentLineSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    product_name = serializers.CharField(source="product.__str__", read_only=True)
    received = serializers.SerializerMethodField()
    remaining = serializers.SerializerMethodField()
    over_received = serializers.BooleanField(read_only=True)
    status = serializers.CharField(read_only=True)

    class Meta:
        model = ShipmentLine
        fields = [
            "id",
            "product",
            "product_name",
            "quantity",
            "received",
            "remaining",
            "over_received",
            "status",
            "notes",
        ]

    def get_received(self, obj):
        agg = getattr(obj, "received_qty_agg", None)
        return str(agg if agg is not None else obj.received_qty)

    def get_remaining(self, obj):
        agg = getattr(obj, "remaining_qty_agg", None)
        return str(agg if agg is not None else obj.remaining_qty)

    def validate(self, attrs):
        quantity = attrs.get("quantity", getattr(self.instance, "quantity", None))
        if quantity is not None and quantity <= 0:
            raise serializers.ValidationError({"quantity": "Quantity must be positive."})
        return attrs


class ShipmentSerializer(serializers.ModelSerializer):
    lines = ShipmentLineSerializer(many=True)
    from_location_name = serializers.CharField(source="from_location.name", read_only=True)
    to_location_name = serializers.CharField(source="to_location.name", read_only=True)
    status = serializers.CharField(read_only=True)
    # Ship immediately on create (mirrors collected_qty at purchase entry);
    # otherwise the shipment stays a draft until the explicit ship action.
    ship = serializers.BooleanField(required=False, default=False, write_only=True)
    created_by_username = serializers.CharField(
        source="created_by.username", read_only=True, default=None
    )

    class Meta:
        model = Shipment
        fields = [
            "id",
            "shipment_no",
            "shipment_date",
            "from_location",
            "from_location_name",
            "to_location",
            "to_location_name",
            "shipment_type",
            "shipping_cost",
            "status",
            "notes",
            "cancel_reason",
            "ship",
            "lines",
            "created_by_username",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["shipment_no", "cancel_reason"]

    def validate(self, attrs):
        from_location = attrs.get(
            "from_location", getattr(self.instance, "from_location", None)
        )
        to_location = attrs.get("to_location", getattr(self.instance, "to_location", None))
        if from_location is not None and from_location == to_location:
            raise serializers.ValidationError(
                {"to_location": "Destination must differ from the source."}
            )
        for location in (from_location, to_location):
            if location is not None and not location.is_active:
                raise serializers.ValidationError(
                    {"location": f"{location.name} is not an active location."}
                )
        return attrs


class ReceiptLineSerializer(serializers.Serializer):
    shipment_line = serializers.PrimaryKeyRelatedField(
        queryset=ShipmentLine.objects.filter(is_deleted=False)
    )
    quantity = serializers.DecimalField(max_digits=14, decimal_places=2)
    product_name = serializers.CharField(
        source="shipment_line.product.__str__", read_only=True
    )


class ShipmentReceiptSerializer(serializers.ModelSerializer):
    lines = ReceiptLineSerializer(many=True)
    created_by_username = serializers.CharField(
        source="created_by.username", read_only=True, default=None
    )

    class Meta:
        model = ShipmentReceipt
        fields = [
            "id",
            "shipment",
            "receipt_date",
            "notes",
            "lines",
            "created_by_username",
            "created_at",
        ]
        read_only_fields = ["shipment"]
