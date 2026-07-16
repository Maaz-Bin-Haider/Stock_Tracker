from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from apps.accounts.views import LoginView, LogoutView, MeView, UserViewSet
from apps.audits.views import AuditLogViewSet
from apps.core.views import health
from apps.inventory.views import (
    StockAdjustmentViewSet,
    StockBalanceViewSet,
    StockLedgerViewSet,
)
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
from apps.purchases.views import PurchaseViewSet
from apps.reports.views import (
    DashboardView,
    ExportCreateView,
    ExportJobViewSet,
    ReportDataView,
    ReportIndexView,
)
from apps.sales.views import SaleViewSet
from apps.shipments.views import ShipmentViewSet

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
router.register("purchases", PurchaseViewSet)
router.register("shipments", ShipmentViewSet)
router.register("sales", SaleViewSet)
router.register("stock-adjustments", StockAdjustmentViewSet)
router.register("stock/ledger", StockLedgerViewSet, basename="stock-ledger")
router.register("stock/balances", StockBalanceViewSet, basename="stock-balances")
router.register("audit", AuditLogViewSet)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/health/", health, name="health"),
    path("api/v1/auth/login/", LoginView.as_view(), name="auth-login"),
    path("api/v1/auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("api/v1/auth/me/", MeView.as_view(), name="auth-me"),
    # Fixed report paths must precede the <slug:key> catch-all.
    path("api/v1/reports/dashboard/", DashboardView.as_view(), name="reports-dashboard"),
    path(
        "api/v1/reports/exports/",
        ExportJobViewSet.as_view({"get": "list"}),
        name="report-exports",
    ),
    path(
        "api/v1/reports/exports/<int:pk>/",
        ExportJobViewSet.as_view({"get": "retrieve"}),
        name="report-export-detail",
    ),
    path(
        "api/v1/reports/exports/<int:pk>/download/",
        ExportJobViewSet.as_view({"get": "download"}),
        name="report-export-download",
    ),
    path("api/v1/reports/", ReportIndexView.as_view(), name="reports-index"),
    path("api/v1/reports/<slug:key>/", ReportDataView.as_view(), name="report-data"),
    path("api/v1/reports/<slug:key>/export/", ExportCreateView.as_view(), name="report-export"),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/v1/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("api/v1/", include(router.urls)),
]
