from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from apps.accounts.views import LoginView, LogoutView, MeView, UserViewSet
from apps.audits.views import AuditLogViewSet
from apps.core.views import health
from apps.masterdata.views import (
    CategoryViewSet,
    CurrencyViewSet,
    CustomerViewSet,
    ExchangeRateViewSet,
    GstRateViewSet,
    LocationViewSet,
    SupplierViewSet,
)
from apps.products.views import ProductViewSet

router = DefaultRouter()
router.register("users", UserViewSet)
router.register("categories", CategoryViewSet)
router.register("locations", LocationViewSet)
router.register("currencies", CurrencyViewSet)
router.register("exchange-rates", ExchangeRateViewSet)
router.register("gst-rates", GstRateViewSet)
router.register("suppliers", SupplierViewSet)
router.register("customers", CustomerViewSet)
router.register("products", ProductViewSet)
router.register("audit", AuditLogViewSet)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/health/", health, name="health"),
    path("api/v1/auth/login/", LoginView.as_view(), name="auth-login"),
    path("api/v1/auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("api/v1/auth/me/", MeView.as_view(), name="auth-me"),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/v1/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("api/v1/", include(router.urls)),
]
