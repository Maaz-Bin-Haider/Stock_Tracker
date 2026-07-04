from rest_framework import serializers

from .models import Product


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "sku",
            "name",
            "category",
            "category_name",
            "brand",
            "model",
            "storage_specs",
            "is_active",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        name = attrs.get("name", getattr(self.instance, "name", ""))
        specs = attrs.get("storage_specs", getattr(self.instance, "storage_specs", ""))
        queryset = Product.objects.filter(name__iexact=name, storage_specs__iexact=specs)
        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError(
                "A product with this name and storage/specs already exists."
            )
        return attrs
