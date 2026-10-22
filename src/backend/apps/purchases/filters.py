"""Invoice search and filters shared by the list and its whole-result totals."""

from django import forms
from django.db.models import Exists, F, OuterRef, Q
from django_filters import rest_framework as filters
from rest_framework.filters import OrderingFilter, SearchFilter

from apps.products.models import Product

from .models import Purchase, PurchaseLine, PurchaseStatus, annotate_line_quantities

SEARCH_FIELDS = {
    "all": [
        "invoice_no", "notes", "supplier__name", "location__name",
        "lines__product__name", "lines__product__storage_specs",
        "lines__product__sku", "lines__product__brand", "lines__product__model",
    ],
    "invoice": ["invoice_no"],
    "product": [
        "lines__product__name", "lines__product__storage_specs",
        "lines__product__sku", "lines__product__brand", "lines__product__model",
    ],
    "supplier": ["supplier__name"],
    "location": ["location__name"],
    "notes": ["notes"],
}


class PurchaseSearchFilter(SearchFilter):
    def must_call_distinct(self, queryset, search_fields):
        # DRF's metadata traversal cannot resolve FilteredRelation aliases.
        # filter_queryset below handles deduplication explicitly.
        return False

    def get_search_fields(self, view, request):
        fields = SEARCH_FIELDS.get(request.query_params.get("search_in", "all"), [])
        # Searching a removed line must not make its old product match an invoice.
        # A filtered relation also keeps every word of a product search on one line.
        return [field.replace("lines__", "search_lines__") for field in fields]

    def filter_queryset(self, request, queryset, view):
        result = super().filter_queryset(request, queryset, view)
        return result.distinct() if self.get_search_terms(request) else result


class PurchaseOrderingFilter(OrderingFilter):
    def get_ordering(self, request, queryset, view):
        ordering = list(super().get_ordering(request, queryset, view) or [])
        # Dates/references can repeat. Stable paging must not lose/repeat invoices.
        if not any(field.lstrip("-") == "id" for field in ordering):
            ordering.append("-id")
        return ordering


class PurchaseFilterForm(forms.Form):
    def clean(self):
        data = super().clean()
        start, end = data.get("date_from"), data.get("date_to")
        if start and end and start > end:
            self.add_error("date_to", "End date must be on or after start date.")
        return data


class PurchaseFilter(filters.FilterSet):
    date_from = filters.DateFilter(field_name="purchase_date", lookup_expr="gte")
    date_to = filters.DateFilter(field_name="purchase_date", lookup_expr="lte")
    product = filters.ModelChoiceFilter(queryset=Product.objects.all(), method="filter_product")
    status = filters.ChoiceFilter(choices=PurchaseStatus.choices, method="filter_status")
    search_in = filters.ChoiceFilter(
        choices=[(key, key) for key in SEARCH_FIELDS], method="filter_search_scope",
    )

    class Meta:
        model = Purchase
        fields = ["location", "supplier", "purchase_date"]
        form = PurchaseFilterForm

    def filter_search_scope(self, queryset, name, value):
        return queryset  # Choice validation; the search backend applies the scope.

    def filter_product(self, queryset, name, value):
        return queryset.filter(pk__in=PurchaseLine.objects.filter(
            is_deleted=False, product=value,
        ).values("purchase_id"))

    def filter_status(self, queryset, name, value):
        # Mirror PurchaseLine.status and Purchase.status without joining collection
        # and refund relations together (which would multiply quantities).
        lines = annotate_line_quantities(PurchaseLine.objects.filter(
            purchase=OuterRef("pk"), is_deleted=False,
        )).annotate(
            search_refunded=F("cancelled_pending_qty_agg") + F("refunded_received_qty_agg"),
        )
        open_lines = lines.filter(search_refunded__lt=F("quantity"))
        unfulfilled = open_lines.filter(Q(pending_qty_agg__gt=0) | Q(collected_qty_agg__lte=0))
        cancelled = lines.filter(
            search_refunded__gte=F("quantity"), refunded_received_qty_agg__lte=0,
        )
        # Test only the predicates needed for the selected status. Expanding the
        # full line and invoice CASE expressions repeated the quantity subqueries
        # many times per invoice on real datasets.
        predicates = {
            PurchaseStatus.FULLY_COLLECTED: Exists(open_lines) & ~Exists(unfulfilled),
            PurchaseStatus.PARTIALLY_RECEIVED: (
                Exists(open_lines) & Exists(unfulfilled)
                & Exists(lines.filter(collected_qty_agg__gt=0))
            ),
            PurchaseStatus.PENDING: (
                ~Exists(lines) | (
                    Exists(open_lines) & Exists(unfulfilled)
                    & ~Exists(lines.filter(collected_qty_agg__gt=0))
                )
            ),
            PurchaseStatus.CANCELLED: Exists(lines) & ~Exists(open_lines) & Exists(cancelled),
            PurchaseStatus.REFUNDED: Exists(lines) & ~Exists(open_lines) & ~Exists(cancelled),
        }
        return queryset.filter(predicates[value])
