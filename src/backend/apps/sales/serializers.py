from rest_framework import serializers

from .models import Sale, SaleLine


class SaleLineSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    product_name = serializers.CharField(source="product.__str__", read_only=True)

    class Meta:
        model = SaleLine
        fields = ["id", "product", "product_name", "quantity", "unit_price", "notes"]

    def validate(self, attrs):
        quantity = attrs.get("quantity", getattr(self.instance, "quantity", None))
        if quantity is not None and quantity <= 0:
            raise serializers.ValidationError({"quantity": "Quantity must be positive."})
        price = attrs.get("unit_price")
        if price is not None and price < 0:
            raise serializers.ValidationError({"unit_price": "Sale price cannot be negative."})
        return attrs


class SaleSerializer(serializers.ModelSerializer):
    lines = SaleLineSerializer(many=True)
    location_name = serializers.CharField(source="location.name", read_only=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    created_by_username = serializers.CharField(
        source="created_by.username", read_only=True, default=None
    )

    class Meta:
        model = Sale
        fields = [
            "id",
            "sale_no",
            "sale_date",
            "location",
            "location_name",
            "customer",
            "customer_name",
            "notes",
            "lines",
            "created_by_username",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["sale_no"]

    def validate_location(self, location):
        if not location.is_sales_location or not location.is_active:
            raise serializers.ValidationError(
                f"{location.name} is not an active sales location (FR-068)."
            )
        return location
