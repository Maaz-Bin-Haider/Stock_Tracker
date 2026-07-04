from rest_framework import serializers

from .models import Category, Currency, Customer, ExchangeRate, GstRate, Location, Supplier

TIMESTAMP_FIELDS = ["created_at", "updated_at"]


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "is_active", *TIMESTAMP_FIELDS]


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = [
            "id",
            "name",
            "country",
            "city",
            "can_purchase",
            "is_sales_location",
            "region_group",
            "gst_region",
            "is_active",
            *TIMESTAMP_FIELDS,
        ]


class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = ["id", "code", "name", "is_active", *TIMESTAMP_FIELDS]


class ExchangeRateSerializer(serializers.ModelSerializer):
    currency_code = serializers.CharField(source="currency.code", read_only=True)

    class Meta:
        model = ExchangeRate
        fields = [
            "id",
            "currency",
            "currency_code",
            "rate_to_aed",
            "effective_date",
            "is_active",
            *TIMESTAMP_FIELDS,
        ]


class GstRateSerializer(serializers.ModelSerializer):
    location_name = serializers.CharField(source="location.name", read_only=True)

    class Meta:
        model = GstRate
        fields = [
            "id",
            "location",
            "location_name",
            "rate",
            "effective_from",
            "effective_to",
            "is_active",
            *TIMESTAMP_FIELDS,
        ]


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = [
            "id",
            "code",
            "name",
            "contact_person",
            "phone",
            "email",
            "country",
            "city",
            "address",
            "notes",
            "is_active",
            *TIMESTAMP_FIELDS,
        ]


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = [
            "id",
            "code",
            "name",
            "phone",
            "email",
            "country",
            "city",
            "address",
            "notes",
            "is_active",
            *TIMESTAMP_FIELDS,
        ]
