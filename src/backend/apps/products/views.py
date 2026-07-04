from apps.core.viewsets import AuditedModelViewSet

from .models import Product
from .serializers import ProductSerializer


class ProductViewSet(AuditedModelViewSet):
    module = "products"
    queryset = Product.objects.select_related("category")
    serializer_class = ProductSerializer
    filterset_fields = ["category", "brand", "is_active"]
    search_fields = ["name", "sku", "brand", "model", "storage_specs"]
