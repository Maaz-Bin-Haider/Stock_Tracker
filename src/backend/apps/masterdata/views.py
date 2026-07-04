from apps.core.viewsets import AuditedModelViewSet

from .models import Category, Currency, Customer, ExchangeRate, GstRate, Location, Supplier
from .serializers import (
    CategorySerializer,
    CurrencySerializer,
    CustomerSerializer,
    ExchangeRateSerializer,
    GstRateSerializer,
    LocationSerializer,
    SupplierSerializer,
)


class CategoryViewSet(AuditedModelViewSet):
    module = "categories"
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    filterset_fields = ["is_active"]
    search_fields = ["name"]


class LocationViewSet(AuditedModelViewSet):
    module = "locations"
    queryset = Location.objects.all()
    serializer_class = LocationSerializer
    filterset_fields = ["can_purchase", "is_sales_location", "is_active", "region_group"]
    search_fields = ["name", "country", "city"]


class CurrencyViewSet(AuditedModelViewSet):
    module = "currencies"
    queryset = Currency.objects.all()
    serializer_class = CurrencySerializer
    filterset_fields = ["is_active"]
    search_fields = ["code", "name"]


class ExchangeRateViewSet(AuditedModelViewSet):
    module = "exchange_rates"
    queryset = ExchangeRate.objects.select_related("currency")
    serializer_class = ExchangeRateSerializer
    filterset_fields = ["currency", "is_active", "effective_date"]
    ordering_fields = ["effective_date"]


class GstRateViewSet(AuditedModelViewSet):
    module = "gst_rates"
    queryset = GstRate.objects.select_related("location")
    serializer_class = GstRateSerializer
    filterset_fields = ["location", "is_active"]
    ordering_fields = ["effective_from"]


class SupplierViewSet(AuditedModelViewSet):
    module = "suppliers"
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    filterset_fields = ["is_active", "country", "city"]
    search_fields = ["name", "code", "contact_person", "phone", "email"]


class CustomerViewSet(AuditedModelViewSet):
    module = "customers"
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    filterset_fields = ["is_active", "country", "city"]
    search_fields = ["name", "code", "phone", "email"]
