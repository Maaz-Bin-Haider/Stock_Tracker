from decimal import Decimal

from rest_framework import serializers

from apps.masterdata.models import ExchangeRate, GstRate

from .models import Purchase, PurchaseCollection, PurchaseLine


class PurchaseLineSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    product_name = serializers.CharField(source="product.__str__", read_only=True)
    currency_code = serializers.CharField(source="currency.code", read_only=True)
    # Optional at entry time only: quantities already in hand when the invoice
    # is recorded (activity diagram 2.2). Later collection goes through the
    # collection workflow, never through purchase edits.
    collected_qty = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        required=False,
        default=None,
        allow_null=True,
        write_only=True,
    )
    collected = serializers.SerializerMethodField()
    pending = serializers.SerializerMethodField()
    status = serializers.CharField(read_only=True)

    class Meta:
        model = PurchaseLine
        fields = [
            "id",
            "product",
            "product_name",
            "quantity",
            "unit_price",
            "currency",
            "currency_code",
            "exchange_rate",
            "unit_price_aed",
            "total_value_aed",
            "gst_rate",
            "gst_rate_percent",
            "gst_amount",
            "gst_amount_aed",
            "collected_qty",
            "collected",
            "pending",
            "status",
            "notes",
        ]
        read_only_fields = [
            "unit_price_aed",
            "total_value_aed",
            "gst_amount",
            "gst_amount_aed",
        ]
        extra_kwargs = {
            "exchange_rate": {"required": False, "allow_null": True, "default": None},
            "gst_rate_percent": {"required": False, "allow_null": True, "default": None},
        }

    def get_collected(self, obj):
        agg = getattr(obj, "collected_qty_agg", None)
        return str(agg if agg is not None else obj.collected_qty)

    def get_pending(self, obj):
        agg = getattr(obj, "pending_qty_agg", None)
        return str(agg if agg is not None else obj.pending_qty)

    def validate(self, attrs):
        quantity = attrs.get("quantity", getattr(self.instance, "quantity", None))
        if quantity is not None and quantity <= 0:
            raise serializers.ValidationError({"quantity": "Quantity must be positive."})
        unit_price = attrs.get("unit_price", getattr(self.instance, "unit_price", None))
        if unit_price is not None and unit_price < 0:
            raise serializers.ValidationError({"unit_price": "Unit price cannot be negative."})
        collected = attrs.get("collected_qty")
        if collected is not None and (collected < 0 or collected > quantity):
            raise serializers.ValidationError(
                {"collected_qty": "Collected quantity must be between 0 and the line quantity."}
            )
        return attrs


class PurchaseSerializer(serializers.ModelSerializer):
    lines = PurchaseLineSerializer(many=True)
    location_name = serializers.CharField(source="location.name", read_only=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    status = serializers.CharField(read_only=True)
    created_by_username = serializers.CharField(
        source="created_by.username", read_only=True, default=None
    )

    class Meta:
        model = Purchase
        fields = [
            "id",
            "invoice_no",
            "purchase_date",
            "location",
            "location_name",
            "supplier",
            "supplier_name",
            "status",
            "notes",
            "lines",
            "created_by_username",
            "created_at",
            "updated_at",
        ]

    def validate_location(self, location):
        if not location.can_purchase or not location.is_active:
            raise serializers.ValidationError(
                f"{location.name} is not an active purchase location (FR-026)."
            )
        return location

    def validate(self, attrs):
        purchase_date = attrs.get(
            "purchase_date", getattr(self.instance, "purchase_date", None)
        )
        location = attrs.get("location", getattr(self.instance, "location", None))
        for line in attrs.get("lines", []):
            self._resolve_frozen_rates(line, purchase_date, location)
        return attrs

    def _resolve_frozen_rates(self, line, purchase_date, location):
        """Fill exchange rate and GST rate defaults from Settings, frozen into
        the line (FR-088/FR-089/FR-090…FR-092). Explicit values win."""
        if line.get("exchange_rate") is None:
            rate = (
                ExchangeRate.objects.filter(
                    currency=line["currency"],
                    is_active=True,
                    effective_date__lte=purchase_date,
                )
                .order_by("-effective_date")
                .first()
            )
            if rate is None:
                raise serializers.ValidationError(
                    {
                        "lines": (
                            f"No exchange rate for {line['currency'].code} on or before "
                            f"{purchase_date}; set one in Settings or override it here."
                        )
                    }
                )
            line["exchange_rate"] = rate.rate_to_aed

        if line.get("gst_rate_percent") is None:
            gst_rate = line.get("gst_rate")
            if gst_rate is None and location is not None and location.gst_region:
                gst_rate = (
                    GstRate.objects.filter(
                        location=location,
                        is_active=True,
                        effective_from__lte=purchase_date,
                    )
                    .exclude(effective_to__lt=purchase_date)
                    .order_by("-effective_from")
                    .first()
                )
                if gst_rate is None:
                    raise serializers.ValidationError(
                        {
                            "lines": (
                                f"{location.name} is a GST region but has no active GST rate "
                                f"for {purchase_date}; add one in Settings or set the rate here."
                            )
                        }
                    )
                line["gst_rate"] = gst_rate
            line["gst_rate_percent"] = gst_rate.rate if gst_rate else Decimal("0.00")


class CollectionLineSerializer(serializers.Serializer):
    purchase_line = serializers.PrimaryKeyRelatedField(
        queryset=PurchaseLine.objects.filter(is_deleted=False)
    )
    quantity = serializers.DecimalField(max_digits=14, decimal_places=2)
    product_name = serializers.CharField(source="purchase_line.product.__str__", read_only=True)


class PurchaseCollectionSerializer(serializers.ModelSerializer):
    lines = CollectionLineSerializer(many=True)
    location_name = serializers.CharField(source="location.name", read_only=True)
    created_by_username = serializers.CharField(
        source="created_by.username", read_only=True, default=None
    )

    class Meta:
        model = PurchaseCollection
        fields = [
            "id",
            "purchase",
            "collection_date",
            "location",
            "location_name",
            "notes",
            "lines",
            "created_by_username",
            "created_at",
        ]
        read_only_fields = ["purchase"]
        # Defaults to the purchase location when omitted (SYSTEM_SPEC §9).
        extra_kwargs = {"location": {"required": False}}
