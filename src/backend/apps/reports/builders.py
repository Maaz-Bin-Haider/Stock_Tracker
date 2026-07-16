"""Builders for every SRS §5 report, registered in ``REPORTS``.

Stock figures come from ``stock_balances`` (or the ledger when a past
``cutoff`` is given — TECHNICAL_ARCHITECTURE §5.3); money/GST figures come
from the values frozen on purchase and refund lines, never from summing
``gst_value`` across ledger rows (see apps.purchases.services notes).

The Upload/File report (SRS §5) is deferred together with the purchase/sale
attachments feature (FR-104…FR-107) — there are no uploads to report yet.
"""

from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Case, DecimalField, F, Max, Sum, When

from apps.audits.models import AuditLog
from apps.core.time import business_day_bounds, business_today
from apps.inventory.models import Bucket, StockAdjustment, StockBalance, StockLedgerEntry
from apps.masterdata.models import Location
from apps.products.models import Product
from apps.purchases.models import (
    PurchaseLine,
    PurchaseRefundLine,
    RefundSource,
    annotate_line_quantities,
)
from apps.sales.models import SaleLine
from apps.shipments.models import ShipmentLine, annotate_shipment_line_quantities

from .definitions import Column, Report, ReportResult, Section

ZERO = Decimal("0.00")
TWO_PLACES = Decimal("0.01")
BUCKETS = (Bucket.PHYSICAL, Bucket.IN_TRANSIT, Bucket.PENDING)


def _money(value) -> Decimal:
    return (value or ZERO).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def _txn_window(filters):
    """UTC window for a business-date range filter on timestamp columns."""
    start = end = None
    if filters.get("date_from"):
        start = business_day_bounds(filters["date_from"])[0]
    if filters.get("date_to"):
        end = business_day_bounds(filters["date_to"])[1]
    return start, end


def _signed_value_sum(field_name):
    return Sum(
        Case(
            When(qty_in__gt=0, then=F(field_name)),
            default=F(field_name) * -1,
            output_field=DecimalField(max_digits=14, decimal_places=2),
        )
    )


def balance_map(filters) -> dict:
    """{(product_id, location_id): {bucket: [qty, value_aed]}}.

    Live figures read ``stock_balances``; with a ``cutoff`` the ledger is
    aggregated with ``txn_at <= cutoff`` instead (FR-096, §5.3).
    """
    cutoff = filters.get("cutoff")
    out: dict = {}
    if cutoff is None:
        rows = StockBalance.objects.all()
        if filters.get("location"):
            rows = rows.filter(location_id=filters["location"])
        if filters.get("product"):
            rows = rows.filter(product_id=filters["product"])
        if filters.get("category"):
            rows = rows.filter(product__category_id=filters["category"])
        for row in rows.values("product_id", "location_id", "bucket", "quantity", "value_aed"):
            key = (row["product_id"], row["location_id"])
            out.setdefault(key, {})[row["bucket"]] = [row["quantity"], row["value_aed"]]
        return out

    entries = StockLedgerEntry.objects.filter(txn_at__lte=cutoff)
    if filters.get("location"):
        entries = entries.filter(location_id=filters["location"])
    if filters.get("product"):
        entries = entries.filter(product_id=filters["product"])
    if filters.get("category"):
        entries = entries.filter(product__category_id=filters["category"])
    rows = entries.values("product_id", "location_id", "bucket").annotate(
        quantity=Sum(F("qty_in") - F("qty_out")),
        value_aed=_signed_value_sum("aed_value"),
    )
    for row in rows:
        key = (row["product_id"], row["location_id"])
        out.setdefault(key, {})[row["bucket"]] = [
            row["quantity"] or ZERO,
            row["value_aed"] or ZERO,
        ]
    return out


def _last_movement_map(filters) -> dict:
    """{(product_id, location_id): last ledger txn_at}."""
    entries = StockLedgerEntry.objects.all()
    if filters.get("cutoff"):
        entries = entries.filter(txn_at__lte=filters["cutoff"])
    rows = entries.values("product_id", "location_id").annotate(last=Max("txn_at"))
    return {(row["product_id"], row["location_id"]): row["last"] for row in rows}


def _products(filters):
    products = Product.objects.select_related("category")
    if filters.get("product"):
        products = products.filter(pk=filters["product"])
    if filters.get("category"):
        products = products.filter(category_id=filters["category"])
    return {product.pk: product for product in products}


def _locations(filters):
    locations = Location.objects.all()
    if filters.get("location"):
        locations = locations.filter(pk=filters["location"])
    return {location.pk: location for location in locations}


def _bucket_qty(buckets: dict, bucket: str) -> Decimal:
    return buckets.get(bucket, [ZERO, ZERO])[0]


def _bucket_value(buckets: dict, bucket: str) -> Decimal:
    return buckets.get(bucket, [ZERO, ZERO])[1]


PRODUCT_COLUMNS = [
    Column("product", "Product"),
    Column("category", "Category"),
    Column("brand", "Brand"),
    Column("model", "Model"),
    Column("storage_specs", "Storage/Specs"),
]


def _product_cells(product: Product) -> dict:
    return {
        "product": product.name,
        "category": product.category.name,
        "brand": product.brand,
        "model": product.model,
        "storage_specs": product.storage_specs,
    }


# ---------------------------------------------------------------- stock views


def build_current_stock_by_location(filters, is_admin) -> ReportResult:
    balances = balance_map(filters)
    products = _products(filters)
    locations = _locations(filters)
    last_moves = _last_movement_map(filters)

    rows = []
    totals = {"Physical": ZERO, "In transit": ZERO, "Pending": ZERO}
    for (product_id, location_id), buckets in balances.items():
        product, location = products.get(product_id), locations.get(location_id)
        if product is None or location is None:
            continue
        physical = _bucket_qty(buckets, Bucket.PHYSICAL)
        in_transit = _bucket_qty(buckets, Bucket.IN_TRANSIT)
        pending = _bucket_qty(buckets, Bucket.PENDING)
        if not any([physical, in_transit, pending]):
            continue
        totals["Physical"] += physical
        totals["In transit"] += in_transit
        totals["Pending"] += pending
        rows.append(
            {
                "location": location.name,
                **_product_cells(product),
                "physical_qty": physical,
                "in_transit_qty": in_transit,
                "pending_qty": pending,
                "negative": physical < 0,
                "last_movement": last_moves.get((product_id, location_id)),
            }
        )
    rows.sort(key=lambda row: (row["location"], row["product"], row["storage_specs"]))
    totals["Rows"] = len(rows)

    columns = [
        Column("location", "Location"),
        *PRODUCT_COLUMNS,
        Column("physical_qty", "Physical", "qty"),
        Column("in_transit_qty", "In transit", "qty"),
        Column("pending_qty", "Pending", "qty"),
        Column("negative", "Negative", "bool"),
        Column("last_movement", "Last movement", "datetime"),
    ]
    return ReportResult([Section("Current Stock by Location", columns, rows)], totals)


def build_total_company_stock(filters, is_admin) -> ReportResult:
    balances = balance_map(filters)
    products = _products(filters)

    per_product: dict = {}
    for (product_id, _location_id), buckets in balances.items():
        agg = per_product.setdefault(
            product_id, {"physical": ZERO, "it": ZERO, "pending": ZERO, "value": ZERO}
        )
        agg["physical"] += _bucket_qty(buckets, Bucket.PHYSICAL)
        agg["it"] += _bucket_qty(buckets, Bucket.IN_TRANSIT)
        agg["pending"] += _bucket_qty(buckets, Bucket.PENDING)
        agg["value"] += sum(_bucket_value(buckets, bucket) for bucket in BUCKETS)

    rows = []
    totals = {"Physical": ZERO, "In transit": ZERO, "Pending": ZERO}
    if is_admin:
        totals["Stock value (AED)"] = ZERO
    for product_id, agg in per_product.items():
        product = products.get(product_id)
        if product is None:
            continue
        total_qty = agg["physical"] + agg["it"] + agg["pending"]
        if not any([agg["physical"], agg["it"], agg["pending"]]):
            continue
        row = {
            "product": product.name,
            "category": product.category.name,
            "storage_specs": product.storage_specs,
            "physical_qty": agg["physical"],
            "in_transit_qty": agg["it"],
            "pending_qty": agg["pending"],
            "total_qty": total_qty,
        }
        totals["Physical"] += agg["physical"]
        totals["In transit"] += agg["it"]
        totals["Pending"] += agg["pending"]
        if is_admin:
            # Stock value is valuation data — admin-only (FR-116), stripped
            # server-side for every other role.
            row["value_aed"] = agg["value"]
            totals["Stock value (AED)"] += agg["value"]
        rows.append(row)
    rows.sort(key=lambda row: (row["product"], row["storage_specs"]))
    totals["Rows"] = len(rows)

    columns = [
        Column("product", "Product"),
        Column("category", "Category"),
        Column("storage_specs", "Storage/Specs"),
        Column("physical_qty", "Physical", "qty"),
        Column("in_transit_qty", "In transit", "qty"),
        Column("pending_qty", "Pending", "qty"),
        Column("total_qty", "Total stock", "qty"),
    ]
    if is_admin:
        columns.append(Column("value_aed", "Stock value (AED)", "money"))
    return ReportResult([Section("Total Company Stock", columns, rows)], totals)


def build_australia_combined_stock(filters, is_admin) -> ReportResult:
    au_locations = list(
        Location.objects.filter(region_group="AU", is_active=True).order_by("name")
    )
    au_ids = [location.pk for location in au_locations]
    balances = balance_map({**filters, "location": None})
    products = _products(filters)

    in_transit_from_au = (
        annotate_shipment_line_quantities(
            ShipmentLine.objects.filter(
                is_deleted=False,
                shipment__is_deleted=False,
                shipment__shipped_at__isnull=False,
                shipment__cancelled_at__isnull=True,
                shipment__from_location_id__in=au_ids,
            )
        )
        .filter(remaining_qty_agg__gt=0)
        .values("product_id")
        .annotate(total=Sum("remaining_qty_agg"))
    )
    transit_map = {row["product_id"]: row["total"] for row in in_transit_from_au}

    rows = []
    for product_id, product in products.items():
        city_qtys = {}
        pending_au = ZERO
        for location in au_locations:
            buckets = balances.get((product_id, location.pk), {})
            city_qtys[f"loc_{location.pk}"] = _bucket_qty(buckets, Bucket.PHYSICAL)
            pending_au += _bucket_qty(buckets, Bucket.PENDING)
        total_au = sum(city_qtys.values(), ZERO)
        transit = transit_map.get(product_id, ZERO)
        if not any([total_au, pending_au, transit]) and not any(city_qtys.values()):
            continue
        rows.append(
            {
                "product": product.name,
                "storage_specs": product.storage_specs,
                **city_qtys,
                "total_au_qty": total_au,
                "pending_au_qty": pending_au,
                "in_transit_from_au_qty": transit,
            }
        )
    rows.sort(key=lambda row: (row["product"], row["storage_specs"]))

    columns = [
        Column("product", "Product"),
        Column("storage_specs", "Storage/Specs"),
        *[Column(f"loc_{location.pk}", location.name, "qty") for location in au_locations],
        Column("total_au_qty", "Total Australia", "qty"),
        Column("pending_au_qty", "Pending Australia", "qty"),
        Column("in_transit_from_au_qty", "In transit from Australia", "qty"),
    ]
    totals = {
        "Total Australia": sum((row["total_au_qty"] for row in rows), ZERO),
        "Pending Australia": sum((row["pending_au_qty"] for row in rows), ZERO),
        "Rows": len(rows),
    }
    return ReportResult([Section("Australia Combined Stock", columns, rows)], totals)


def _build_sales_location_stock(location_name, transit_label):
    def build(filters, is_admin) -> ReportResult:
        location = Location.objects.filter(name__iexact=location_name).first()
        columns = [
            Column("product", "Product"),
            Column("category", "Category"),
            Column("storage_specs", "Storage/Specs"),
            Column("available_qty", "Available", "qty"),
            Column("in_transit_qty", transit_label, "qty"),
            Column("sold_today_qty", "Sold today", "qty"),
            Column("negative", "Negative", "bool"),
        ]
        title = f"{location_name} Stock"
        if location is None:
            return ReportResult([Section(title, columns, [])], {"Rows": 0})

        balances = balance_map({**filters, "location": location.pk})
        products = _products(filters)
        sold_today = (
            SaleLine.objects.filter(
                is_deleted=False,
                sale__is_deleted=False,
                sale__location=location,
                sale__sale_date=business_today(),
            )
            .values("product_id")
            .annotate(total=Sum("quantity"))
        )
        sold_map = {row["product_id"]: row["total"] for row in sold_today}

        rows = []
        totals = {"Available": ZERO, "Sold today": ZERO}
        for (product_id, _location_id), buckets in balances.items():
            product = products.get(product_id)
            if product is None:
                continue
            available = _bucket_qty(buckets, Bucket.PHYSICAL)
            in_transit = _bucket_qty(buckets, Bucket.IN_TRANSIT)
            sold = sold_map.get(product_id, ZERO)
            if not any([available, in_transit, sold]):
                continue
            totals["Available"] += available
            totals["Sold today"] += sold
            rows.append(
                {
                    "product": product.name,
                    "category": product.category.name,
                    "storage_specs": product.storage_specs,
                    "available_qty": available,
                    "in_transit_qty": in_transit,
                    "sold_today_qty": sold,
                    "negative": available < 0,
                }
            )
        rows.sort(key=lambda row: (row["product"], row["storage_specs"]))
        totals["Rows"] = len(rows)
        return ReportResult([Section(title, columns, rows)], totals)

    return build


# ------------------------------------------------------------- purchase views


def _purchase_lines(filters):
    lines = annotate_line_quantities(
        PurchaseLine.objects.filter(is_deleted=False, purchase__is_deleted=False)
    ).select_related(
        "purchase__supplier", "purchase__location", "product__category", "currency", "created_by"
    )
    if filters.get("date_from"):
        lines = lines.filter(purchase__purchase_date__gte=filters["date_from"])
    if filters.get("date_to"):
        lines = lines.filter(purchase__purchase_date__lte=filters["date_to"])
    if filters.get("location"):
        lines = lines.filter(purchase__location_id=filters["location"])
    if filters.get("product"):
        lines = lines.filter(product_id=filters["product"])
    if filters.get("category"):
        lines = lines.filter(product__category_id=filters["category"])
    if filters.get("supplier"):
        lines = lines.filter(purchase__supplier_id=filters["supplier"])
    return lines.order_by("purchase__purchase_date", "purchase_id", "id")


def build_pending_purchase_stock(filters, is_admin) -> ReportResult:
    lines = _purchase_lines(filters).filter(pending_qty_agg__gt=0)
    rows = []
    totals = {"Pending qty": ZERO, "AED value pending": ZERO, "GST pending (AED)": ZERO}
    for line in lines:
        pending = line.pending_qty
        aed_pending = _money(pending * line.unit_price_aed)
        gst_pending = (
            _money(line.gst_amount_aed * pending / line.quantity) if line.quantity else ZERO
        )
        totals["Pending qty"] += pending
        totals["AED value pending"] += aed_pending
        totals["GST pending (AED)"] += gst_pending
        rows.append(
            {
                "supplier": line.purchase.supplier.name,
                "invoice_no": line.purchase.invoice_no,
                "purchase_date": line.purchase.purchase_date,
                "location": line.purchase.location.name,
                "product": str(line.product),
                "purchased_qty": line.quantity,
                "collected_qty": line.collected_qty,
                "pending_qty": pending,
                "cancelled_qty": line.cancelled_pending_qty,
                "aed_value_pending": aed_pending,
                "gst_pending": gst_pending,
                "status": line.status,
            }
        )
    totals["Rows"] = len(rows)
    columns = [
        Column("supplier", "Supplier/Party"),
        Column("invoice_no", "Invoice"),
        Column("purchase_date", "Purchase date", "date"),
        Column("location", "Location"),
        Column("product", "Product"),
        Column("purchased_qty", "Purchased", "qty"),
        Column("collected_qty", "Collected", "qty"),
        Column("pending_qty", "Pending", "qty"),
        Column("cancelled_qty", "Cancelled/refunded pending", "qty"),
        Column("aed_value_pending", "AED value pending", "money"),
        Column("gst_pending", "GST pending (AED)", "money"),
        Column("status", "Status"),
    ]
    return ReportResult([Section("Pending Purchase Stock", columns, rows)], totals)


def build_pending_purchase_by_location(filters, is_admin) -> ReportResult:
    lines = _purchase_lines(filters).filter(pending_qty_agg__gt=0)
    grouped: dict = {}
    for line in lines:
        key = (line.purchase.location.name, str(line.product))
        agg = grouped.setdefault(
            key,
            {
                "purchased": ZERO,
                "collected": ZERO,
                "pending": ZERO,
                "cancelled": ZERO,
                "suppliers": set(),
                "oldest": None,
            },
        )
        agg["purchased"] += line.quantity
        agg["collected"] += line.collected_qty
        agg["pending"] += line.pending_qty
        agg["cancelled"] += line.cancelled_pending_qty
        agg["suppliers"].add(line.purchase.supplier.name)
        date = line.purchase.purchase_date
        agg["oldest"] = date if agg["oldest"] is None else min(agg["oldest"], date)

    rows = [
        {
            "location": location,
            "product": product,
            "purchased_qty": agg["purchased"],
            "collected_qty": agg["collected"],
            "pending_qty": agg["pending"],
            "cancelled_qty": agg["cancelled"],
            "suppliers": ", ".join(sorted(agg["suppliers"])),
            "oldest_pending_date": agg["oldest"],
        }
        for (location, product), agg in sorted(grouped.items())
    ]
    totals = {"Pending qty": sum((row["pending_qty"] for row in rows), ZERO), "Rows": len(rows)}
    columns = [
        Column("location", "Location"),
        Column("product", "Product"),
        Column("purchased_qty", "Total purchased", "qty"),
        Column("collected_qty", "Total collected", "qty"),
        Column("pending_qty", "Total pending", "qty"),
        Column("cancelled_qty", "Cancelled/refunded", "qty"),
        Column("suppliers", "Suppliers/Parties"),
        Column("oldest_pending_date", "Oldest pending date", "date"),
    ]
    return ReportResult([Section("Pending Purchase Stock by Location", columns, rows)], totals)


PURCHASE_REPORT_COLUMNS = [
    Column("invoice_no", "Invoice"),
    Column("purchase_date", "Purchase date", "date"),
    Column("supplier", "Supplier/Party"),
    Column("location", "Location"),
    Column("product", "Product"),
    Column("category", "Category"),
    Column("quantity", "Quantity", "qty"),
    Column("collected_qty", "Collected", "qty"),
    Column("pending_qty", "Pending", "qty"),
    Column("refunded_qty", "Refunded/cancelled", "qty"),
    Column("unit_price", "Unit price", "money"),
    Column("currency", "Currency"),
    Column("exchange_rate", "Exchange rate", "qty"),
    Column("unit_price_aed", "AED unit price", "money"),
    Column("total_value_aed", "AED total", "money"),
    Column("gst_rate_percent", "GST rate %", "percent"),
    Column("gst_amount", "GST amount", "money"),
    Column("status", "Status"),
    Column("created_by", "Created by"),
]


def _purchase_report_rows(filters):
    rows = []
    for line in _purchase_lines(filters):
        status = line.status
        if filters.get("status") and status != filters["status"]:
            continue
        rows.append(
            {
                "invoice_no": line.purchase.invoice_no,
                "purchase_date": line.purchase.purchase_date,
                "supplier": line.purchase.supplier.name,
                "location": line.purchase.location.name,
                "product": str(line.product),
                "category": line.product.category.name,
                "quantity": line.quantity,
                "collected_qty": line.collected_qty,
                "pending_qty": line.pending_qty,
                "refunded_qty": line.refunded_qty,
                "unit_price": line.unit_price,
                "currency": line.currency.code,
                "exchange_rate": line.exchange_rate,
                "unit_price_aed": line.unit_price_aed,
                "total_value_aed": line.total_value_aed,
                "gst_rate_percent": line.gst_rate_percent,
                "gst_amount": line.gst_amount,
                "status": status,
                "created_by": line.created_by.username if line.created_by else "",
            }
        )
    return rows


def _purchase_totals(rows):
    return {
        "Quantity": sum((row["quantity"] for row in rows), ZERO),
        "Pending": sum((row["pending_qty"] for row in rows), ZERO),
        "AED total": sum((row["total_value_aed"] for row in rows), ZERO),
        "Rows": len(rows),
    }


def build_purchase_report(filters, is_admin) -> ReportResult:
    rows = _purchase_report_rows(filters)
    return ReportResult(
        [Section("Purchase Report", PURCHASE_REPORT_COLUMNS, rows)], _purchase_totals(rows)
    )


def build_party_wise_purchases(filters, is_admin) -> ReportResult:
    rows = _purchase_report_rows(filters)
    rows.sort(key=lambda row: (row["supplier"], row["purchase_date"], row["invoice_no"]))
    columns = [
        Column("supplier", "Supplier/Party"),
        *[column for column in PURCHASE_REPORT_COLUMNS if column.key not in ("supplier",)],
    ]
    return ReportResult(
        [Section("Party-wise Purchase Records", columns, rows)], _purchase_totals(rows)
    )


# ---------------------------------------------------------------- GST report


def build_gst_report(filters, is_admin) -> ReportResult:
    """Product-line-level GST report (SRS §5.1): net quantity and net GST
    from purchase/refund line values frozen at entry/refund time — never
    from summing ledger gst_value rows."""
    from django.db.models import Q

    lines = (
        _purchase_lines(filters)
        .filter(Q(purchase__location__gst_region__gt="") | Q(gst_amount__gt=0))
        .prefetch_related("refund_lines__refund")
    )
    rows = []
    totals = {"GST (AED)": ZERO, "GST reversed (AED)": ZERO, "Net GST (AED)": ZERO}
    for line in lines:
        refund_lines = [
            refund_line
            for refund_line in line.refund_lines.all()
            if not refund_line.refund.is_deleted
        ]
        gst_reversal = sum((refund_line.gst_reversal for refund_line in refund_lines), ZERO)
        gst_reversal_aed = sum(
            (refund_line.gst_reversal_aed for refund_line in refund_lines), ZERO
        )
        refund_refs = ", ".join(
            sorted({refund_line.refund.refund_no for refund_line in refund_lines})
        )
        refund_date = max(
            (refund_line.refund.refund_date for refund_line in refund_lines), default=None
        )
        net_gst = line.gst_amount - gst_reversal
        totals["GST (AED)"] += line.gst_amount_aed
        totals["GST reversed (AED)"] += gst_reversal_aed
        totals["Net GST (AED)"] += line.gst_amount_aed - gst_reversal_aed
        rows.append(
            {
                "invoice_no": line.purchase.invoice_no,
                "purchase_date": line.purchase.purchase_date,
                "invoice_status": line.purchase.status,
                "location": line.purchase.location.name,
                "gst_region": line.purchase.location.gst_region,
                "product": line.product.name,
                "storage_specs": line.product.storage_specs,
                "net_qty": line.net_qty,
                "unit_price": line.unit_price,
                "currency": line.currency.code,
                "gross_value": _money(line.quantity * line.unit_price),
                "gst_rate_percent": line.gst_rate_percent,
                "gst_amount": line.gst_amount,
                "gst_reversal": gst_reversal,
                "refund_reference": refund_refs,
                "refund_date": refund_date,
                "net_gst": net_gst,
                "line_status": line.status,
                "created_by": line.created_by.username if line.created_by else "",
                "created_at": line.created_at,
                "updated_by": line.updated_by.username if line.updated_by else "",
                "updated_at": line.updated_at,
                "notes": line.notes,
            }
        )
    totals["Rows"] = len(rows)
    columns = [
        Column("invoice_no", "Invoice"),
        Column("purchase_date", "Purchase date", "date"),
        Column("invoice_status", "Invoice status"),
        Column("location", "Location"),
        Column("gst_region", "GST region"),
        Column("product", "Product"),
        Column("storage_specs", "Storage/Specs"),
        Column("net_qty", "Net qty", "qty"),
        Column("unit_price", "Unit price", "money"),
        Column("currency", "Currency"),
        Column("gross_value", "Gross value", "money"),
        Column("gst_rate_percent", "GST rate %", "percent"),
        Column("gst_amount", "GST amount", "money"),
        Column("gst_reversal", "GST reversal", "money"),
        Column("refund_reference", "Refund reference"),
        Column("refund_date", "Refund date", "date"),
        Column("net_gst", "Net GST", "money"),
        Column("line_status", "Line status"),
        Column("created_by", "Created by"),
        Column("created_at", "Created at", "datetime"),
        Column("updated_by", "Updated by"),
        Column("updated_at", "Updated at", "datetime"),
        Column("notes", "Notes"),
    ]
    return ReportResult([Section("GST Report", columns, rows)], totals)


# ------------------------------------------------------------ other flows


def build_refund_report(filters, is_admin) -> ReportResult:
    lines = PurchaseRefundLine.objects.filter(refund__is_deleted=False).select_related(
        "refund__purchase__supplier",
        "refund__created_by",
        "purchase_line__product",
        "location",
    )
    if filters.get("date_from"):
        lines = lines.filter(refund__refund_date__gte=filters["date_from"])
    if filters.get("date_to"):
        lines = lines.filter(refund__refund_date__lte=filters["date_to"])
    if filters.get("supplier"):
        lines = lines.filter(refund__purchase__supplier_id=filters["supplier"])
    if filters.get("product"):
        lines = lines.filter(purchase_line__product_id=filters["product"])
    if filters.get("location"):
        lines = lines.filter(location_id=filters["location"])

    rows = []
    totals = {"Qty refunded": ZERO, "AED reversed": ZERO, "GST reversed (AED)": ZERO}
    for line in lines.order_by("refund__refund_date", "refund_id", "id"):
        totals["Qty refunded"] += line.quantity
        totals["AED reversed"] += line.value_reversal_aed
        totals["GST reversed (AED)"] += line.gst_reversal_aed
        rows.append(
            {
                "refund_no": line.refund.refund_no,
                "refund_date": line.refund.refund_date,
                "invoice_no": line.refund.purchase.invoice_no,
                "supplier": line.refund.purchase.supplier.name,
                "product": str(line.purchase_line.product),
                "quantity": line.quantity,
                "original_qty": line.purchase_line.quantity,
                "received_qty_affected": (
                    line.quantity if line.source == RefundSource.RECEIVED else ZERO
                ),
                "pending_qty_affected": (
                    line.quantity if line.source == RefundSource.PENDING else ZERO
                ),
                "value_reversal_aed": line.value_reversal_aed,
                "gst_reversal_aed": line.gst_reversal_aed,
                "reason": line.refund.reason,
                "created_by": (
                    line.refund.created_by.username if line.refund.created_by else ""
                ),
            }
        )
    totals["Rows"] = len(rows)
    columns = [
        Column("refund_no", "Refund/Cancellation"),
        Column("refund_date", "Date", "date"),
        Column("invoice_no", "Purchase invoice"),
        Column("supplier", "Supplier/Party"),
        Column("product", "Product"),
        Column("quantity", "Qty refunded/cancelled", "qty"),
        Column("original_qty", "Original qty", "qty"),
        Column("received_qty_affected", "Received qty affected", "qty"),
        Column("pending_qty_affected", "Pending qty affected", "qty"),
        Column("value_reversal_aed", "AED value reversed", "money"),
        Column("gst_reversal_aed", "GST reversed (AED)", "money"),
        Column("reason", "Reason"),
        Column("created_by", "Created by"),
    ]
    return ReportResult([Section("Refund/Cancellation Report", columns, rows)], totals)


def build_in_transit_stock(filters, is_admin) -> ReportResult:
    lines = annotate_shipment_line_quantities(
        ShipmentLine.objects.filter(
            is_deleted=False,
            shipment__is_deleted=False,
            shipment__shipped_at__isnull=False,
            shipment__cancelled_at__isnull=True,
        )
    ).select_related("shipment__from_location", "shipment__to_location", "product")
    if filters.get("date_from"):
        lines = lines.filter(shipment__shipment_date__gte=filters["date_from"])
    if filters.get("date_to"):
        lines = lines.filter(shipment__shipment_date__lte=filters["date_to"])
    if filters.get("product"):
        lines = lines.filter(product_id=filters["product"])
    if filters.get("category"):
        lines = lines.filter(product__category_id=filters["category"])
    if filters.get("location"):
        from django.db.models import Q

        lines = lines.filter(
            Q(shipment__from_location_id=filters["location"])
            | Q(shipment__to_location_id=filters["location"])
        )

    rows = []
    totals = {"Shipped": ZERO, "Received": ZERO, "Remaining in transit": ZERO}
    for line in lines.exclude(remaining_qty_agg=0).order_by(
        "shipment__shipment_date", "shipment_id", "id"
    ):
        status = line.status
        if filters.get("status") and status != filters["status"]:
            continue
        received = line.received_qty
        remaining = line.remaining_qty
        totals["Shipped"] += line.quantity
        totals["Received"] += received
        totals["Remaining in transit"] += remaining
        rows.append(
            {
                "shipment_no": line.shipment.shipment_no,
                "shipment_date": line.shipment.shipment_date,
                "from_location": line.shipment.from_location.name,
                "to_location": line.shipment.to_location.name,
                "product": str(line.product),
                "shipped_qty": line.quantity,
                "received_qty": received,
                "remaining_qty": remaining,
                "over_received_qty": max(received - line.quantity, ZERO),
                "status": status,
            }
        )
    totals["Rows"] = len(rows)
    columns = [
        Column("shipment_no", "Shipment"),
        Column("shipment_date", "Shipment date", "date"),
        Column("from_location", "From"),
        Column("to_location", "To"),
        Column("product", "Product"),
        Column("shipped_qty", "Shipped", "qty"),
        Column("received_qty", "Received", "qty"),
        Column("remaining_qty", "Remaining", "qty"),
        Column("over_received_qty", "Over-received", "qty"),
        Column("status", "Status"),
    ]
    return ReportResult([Section("In-Transit Stock", columns, rows)], totals)


def _sale_lines(filters):
    lines = SaleLine.objects.filter(is_deleted=False, sale__is_deleted=False).select_related(
        "sale__location", "sale__customer", "sale__created_by", "product"
    )
    if filters.get("date_from"):
        lines = lines.filter(sale__sale_date__gte=filters["date_from"])
    if filters.get("date_to"):
        lines = lines.filter(sale__sale_date__lte=filters["date_to"])
    if filters.get("location"):
        lines = lines.filter(sale__location_id=filters["location"])
    if filters.get("product"):
        lines = lines.filter(product_id=filters["product"])
    if filters.get("category"):
        lines = lines.filter(product__category_id=filters["category"])
    if filters.get("customer"):
        lines = lines.filter(sale__customer_id=filters["customer"])
    return lines.order_by("sale__sale_date", "sale_id", "id")


SALES_REPORT_COLUMNS = [
    Column("sale_no", "Sale reference"),
    Column("sale_date", "Sale date", "date"),
    Column("location", "Location"),
    Column("customer", "Customer"),
    Column("product", "Product"),
    Column("quantity", "Quantity", "qty"),
    Column("unit_price", "Sale price (reference)", "money"),
    Column("notes", "Notes"),
    Column("created_by", "Created by"),
]


def _sales_rows(filters):
    rows = []
    for line in _sale_lines(filters):
        rows.append(
            {
                "sale_no": line.sale.sale_no,
                "sale_date": line.sale.sale_date,
                "location": line.sale.location.name,
                "customer": line.sale.customer.name,
                "product": str(line.product),
                "quantity": line.quantity,
                "unit_price": line.unit_price,
                "notes": line.notes or line.sale.notes,
                "created_by": line.sale.created_by.username if line.sale.created_by else "",
            }
        )
    return rows


def _sales_totals(rows):
    return {
        "Quantity": sum((row["quantity"] for row in rows), ZERO),
        "Reference sale value": sum(
            (row["quantity"] * row["unit_price"] for row in rows if row["unit_price"]), ZERO
        ),
        "Rows": len(rows),
    }


def build_sales_report(filters, is_admin) -> ReportResult:
    rows = _sales_rows(filters)
    return ReportResult([Section("Sales Report", SALES_REPORT_COLUMNS, rows)], _sales_totals(rows))


def build_party_wise_sales(filters, is_admin) -> ReportResult:
    rows = _sales_rows(filters)
    rows.sort(key=lambda row: (row["customer"], row["sale_date"], row["sale_no"]))
    columns = [
        Column("customer", "Customer"),
        *[column for column in SALES_REPORT_COLUMNS if column.key != "customer"],
    ]
    return ReportResult([Section("Party-wise Sale Records", columns, rows)], _sales_totals(rows))


def build_stock_ledger_report(filters, is_admin) -> ReportResult:
    entries = StockLedgerEntry.objects.select_related(
        "product", "location", "created_by"
    ).order_by("txn_at", "id")
    start, end = _txn_window(filters)
    if start:
        entries = entries.filter(txn_at__gte=start)
    if end:
        entries = entries.filter(txn_at__lt=end)
    if filters.get("location"):
        entries = entries.filter(location_id=filters["location"])
    if filters.get("product"):
        entries = entries.filter(product_id=filters["product"])
    if filters.get("category"):
        entries = entries.filter(product__category_id=filters["category"])
    if filters.get("bucket"):
        entries = entries.filter(bucket=filters["bucket"])
    if filters.get("txn_type"):
        entries = entries.filter(txn_type=filters["txn_type"])

    rows = []
    totals = {"Qty in": ZERO, "Qty out": ZERO}
    for entry in entries:
        totals["Qty in"] += entry.qty_in
        totals["Qty out"] += entry.qty_out
        rows.append(
            {
                "txn_at": entry.txn_at,
                "txn_type": entry.get_txn_type_display(),
                "source_module": entry.source_module,
                "reference": f"{entry.source_module}#{entry.source_id}",
                "product": str(entry.product),
                "location": entry.location.name,
                "qty_in": entry.qty_in,
                "qty_out": entry.qty_out,
                "net_qty": entry.net_qty,
                "bucket": entry.bucket,
                "aed_value": entry.aed_value,
                "gst_value": entry.gst_value,
                "created_by": entry.created_by.username if entry.created_by else "",
            }
        )
    totals["Net"] = totals["Qty in"] - totals["Qty out"]
    totals["Rows"] = len(rows)
    columns = [
        Column("txn_at", "Date/time", "datetime"),
        Column("txn_type", "Transaction type"),
        Column("source_module", "Source module"),
        Column("reference", "Reference"),
        Column("product", "Product"),
        Column("location", "Location"),
        Column("qty_in", "Qty in", "qty"),
        Column("qty_out", "Qty out", "qty"),
        Column("net_qty", "Net", "qty"),
        Column("bucket", "Bucket"),
        Column("aed_value", "AED value", "money"),
        Column("gst_value", "GST value", "money"),
        Column("created_by", "Created by"),
    ]
    return ReportResult([Section("Stock Ledger Report", columns, rows)], totals)


def build_stock_adjustment_report(filters, is_admin) -> ReportResult:
    adjustments = StockAdjustment.objects.filter(is_deleted=False).select_related(
        "location", "product", "created_by"
    )
    if filters.get("date_from"):
        adjustments = adjustments.filter(adjustment_date__gte=filters["date_from"])
    if filters.get("date_to"):
        adjustments = adjustments.filter(adjustment_date__lte=filters["date_to"])
    if filters.get("location"):
        adjustments = adjustments.filter(location_id=filters["location"])
    if filters.get("product"):
        adjustments = adjustments.filter(product_id=filters["product"])
    if filters.get("adjustment_type"):
        adjustments = adjustments.filter(adjustment_type=filters["adjustment_type"])

    rows = [
        {
            "reference": f"ADJ-{adjustment.pk:06d}",
            "adjustment_date": adjustment.adjustment_date,
            "location": adjustment.location.name,
            "product": str(adjustment.product),
            "adjustment_type": adjustment.adjustment_type,
            "quantity": adjustment.quantity,
            "reason": adjustment.reason,
            "notes": adjustment.notes,
            "created_by": adjustment.created_by.username if adjustment.created_by else "",
        }
        for adjustment in adjustments.order_by("adjustment_date", "id")
    ]
    totals = {"Quantity": sum((row["quantity"] for row in rows), ZERO), "Rows": len(rows)}
    columns = [
        Column("reference", "Adjustment"),
        Column("adjustment_date", "Date", "date"),
        Column("location", "Location"),
        Column("product", "Product"),
        Column("adjustment_type", "Type"),
        Column("quantity", "Quantity", "qty"),
        Column("reason", "Reason"),
        Column("notes", "Notes"),
        Column("created_by", "Created by"),
    ]
    return ReportResult([Section("Stock Adjustment Report", columns, rows)], totals)


def build_user_activity_report(filters, is_admin) -> ReportResult:
    logs = AuditLog.objects.select_related("user").order_by("-created_at", "-id")
    start, end = _txn_window(filters)
    if start:
        logs = logs.filter(created_at__gte=start)
    if end:
        logs = logs.filter(created_at__lt=end)
    if filters.get("user"):
        logs = logs.filter(user_id=filters["user"])
    if filters.get("action"):
        logs = logs.filter(action=filters["action"])
    if filters.get("module"):
        logs = logs.filter(module=filters["module"])

    def _summary(values):
        if not values:
            return ""
        text = ", ".join(f"{key}={value}" for key, value in values.items())
        return text[:160] + ("…" if len(text) > 160 else "")

    rows = [
        {
            "created_at": log.created_at,
            "user": log.user.username if log.user else "system",
            "action": log.action,
            "module": log.module,
            "reference": f"{log.module}#{log.record_id}" if log.record_id else log.record_repr,
            "before_summary": _summary(log.before_values),
            "after_summary": _summary(log.after_values),
            "ip_address": log.ip_address or "",
        }
        for log in logs
    ]
    columns = [
        Column("created_at", "Date/time", "datetime"),
        Column("user", "User"),
        Column("action", "Action"),
        Column("module", "Module"),
        Column("reference", "Record reference"),
        Column("before_summary", "Before"),
        Column("after_summary", "After"),
        Column("ip_address", "IP"),
    ]
    return ReportResult(
        [Section("User Activity Report", columns, rows)], {"Rows": len(rows)}
    )


# ------------------------------------------------------------- valuation


def _valuation_pivot(filters):
    """Rows per (product, location) with per-bucket qty/value — the shared
    base for both valuation views (FR-117/FR-118: weighted average in AED,
    all three buckets counted, shown separately)."""
    balances = balance_map(filters)
    products = _products(filters)
    locations = _locations(filters)
    last_moves = _last_movement_map(filters)

    rows = []
    for (product_id, location_id), buckets in balances.items():
        product, location = products.get(product_id), locations.get(location_id)
        if product is None or location is None:
            continue
        quantities = {bucket: _bucket_qty(buckets, bucket) for bucket in BUCKETS}
        values = {bucket: _bucket_value(buckets, bucket) for bucket in BUCKETS}
        total_qty = sum(quantities.values(), ZERO)
        total_value = sum(values.values(), ZERO)
        if not total_qty and not total_value:
            continue
        rows.append(
            {
                "product": product,
                "location": location,
                "quantities": quantities,
                "values": values,
                "total_qty": total_qty,
                "total_value": total_value,
                "last_movement": last_moves.get((product_id, location_id)),
            }
        )
    return rows


def build_valuation_summary(filters, is_admin) -> ReportResult:
    pivot = _valuation_pivot(filters)

    by_bucket = {bucket: ZERO for bucket in BUCKETS}
    by_location: dict = {}
    by_category: dict = {}
    by_product: dict = {}
    for row in pivot:
        location_agg = by_location.setdefault(
            row["location"].name, {bucket: ZERO for bucket in BUCKETS}
        )
        for bucket in BUCKETS:
            by_bucket[bucket] += row["values"][bucket]
            location_agg[bucket] += row["values"][bucket]
        by_category[row["product"].category.name] = (
            by_category.get(row["product"].category.name, ZERO) + row["total_value"]
        )
        product_agg = by_product.setdefault(str(row["product"]), {"qty": ZERO, "value": ZERO})
        product_agg["qty"] += row["total_qty"]
        product_agg["value"] += row["total_value"]

    total_worth = sum(by_bucket.values(), ZERO)

    bucket_labels = {
        Bucket.PHYSICAL: "Physical",
        Bucket.IN_TRANSIT: "In transit",
        Bucket.PENDING: "Pending",
    }
    bucket_section = Section(
        "Worth by Bucket",
        [Column("bucket", "Bucket"), Column("value", "Value (AED)", "money")],
        [
            {"bucket": bucket_labels[bucket], "value": by_bucket[bucket]}
            for bucket in BUCKETS
        ],
    )
    location_section = Section(
        "Worth by Location",
        [
            Column("location", "Location"),
            Column("physical", "Physical (AED)", "money"),
            Column("in_transit", "In transit (AED)", "money"),
            Column("pending", "Pending (AED)", "money"),
            Column("total", "Total (AED)", "money"),
        ],
        [
            {
                "location": name,
                "physical": values[Bucket.PHYSICAL],
                "in_transit": values[Bucket.IN_TRANSIT],
                "pending": values[Bucket.PENDING],
                "total": sum(values.values(), ZERO),
            }
            for name, values in sorted(by_location.items())
        ],
    )
    category_section = Section(
        "Worth by Category",
        [Column("category", "Category"), Column("value", "Value (AED)", "money")],
        [
            {"category": name, "value": value}
            for name, value in sorted(by_category.items(), key=lambda item: -item[1])
        ],
    )
    top_section = Section(
        "Top Products by Value",
        [
            Column("product", "Product"),
            Column("quantity", "Total qty", "qty"),
            Column("value", "Value (AED)", "money"),
        ],
        [
            {"product": name, "quantity": agg["qty"], "value": agg["value"]}
            for name, agg in sorted(by_product.items(), key=lambda item: -item[1]["value"])[:10]
        ],
    )
    return ReportResult(
        [bucket_section, location_section, category_section, top_section],
        {"Total company stock worth (AED)": total_worth},
    )


def build_valuation_detail(filters, is_admin) -> ReportResult:
    pivot = _valuation_pivot(filters)
    rows = []
    totals = {"Total value (AED)": ZERO}
    for entry in sorted(
        pivot, key=lambda item: (item["location"].name, str(item["product"]))
    ):
        quantities, values = entry["quantities"], entry["values"]
        avg_cost = (
            _money(entry["total_value"] / entry["total_qty"]) if entry["total_qty"] else ZERO
        )
        totals["Total value (AED)"] += entry["total_value"]
        rows.append(
            {
                **_product_cells(entry["product"]),
                "location": entry["location"].name,
                "physical_qty": quantities[Bucket.PHYSICAL],
                "in_transit_qty": quantities[Bucket.IN_TRANSIT],
                "pending_qty": quantities[Bucket.PENDING],
                "avg_unit_cost": avg_cost,
                "physical_value": values[Bucket.PHYSICAL],
                "in_transit_value": values[Bucket.IN_TRANSIT],
                "pending_value": values[Bucket.PENDING],
                "total_value": entry["total_value"],
                "last_movement": entry["last_movement"],
                "negative": quantities[Bucket.PHYSICAL] < 0,
            }
        )
    totals["Rows"] = len(rows)
    columns = [
        *PRODUCT_COLUMNS,
        Column("location", "Location"),
        Column("physical_qty", "Physical qty", "qty"),
        Column("in_transit_qty", "In transit qty", "qty"),
        Column("pending_qty", "Pending qty", "qty"),
        Column("avg_unit_cost", "Weighted avg unit cost (AED)", "money"),
        Column("physical_value", "Physical value (AED)", "money"),
        Column("in_transit_value", "In transit value (AED)", "money"),
        Column("pending_value", "Pending value (AED)", "money"),
        Column("total_value", "Total value (AED)", "money"),
        Column("last_movement", "Last movement", "datetime"),
        Column("negative", "Negative", "bool"),
    ]
    return ReportResult([Section("Stock Valuation Detail", columns, rows)], totals)


# ---------------------------------------------------------------- registry


STOCK_FILTERS = ("location", "product", "category")

REPORTS: dict[str, Report] = {
    report.key: report
    for report in [
        Report(
            "current-stock-by-location",
            "Current Stock by Location",
            "Physical, in-transit, and pending stock per product per location.",
            (*STOCK_FILTERS, "cutoff"),
            build_current_stock_by_location,
        ),
        Report(
            "total-company-stock",
            "Total Company Stock",
            "Company-wide stock per product across all locations.",
            ("product", "category", "cutoff"),
            build_total_company_stock,
        ),
        Report(
            "australia-combined-stock",
            "Australia Combined Stock",
            "Calculated combined view over the Australian cities.",
            ("product", "category"),
            build_australia_combined_stock,
        ),
        Report(
            "dubai-stock",
            "Dubai Stock",
            "Available, inbound, and sold-today stock at Dubai.",
            ("product", "category"),
            _build_sales_location_stock("Dubai", "In transit to Dubai"),
        ),
        Report(
            "karachi-stock",
            "Karachi Stock",
            "Available, inbound (from Dubai), and sold-today stock at Karachi.",
            ("product", "category"),
            _build_sales_location_stock("Karachi", "In transit from Dubai"),
        ),
        Report(
            "pending-purchase-stock",
            "Pending Purchase Stock",
            "Purchased but not yet collected quantities per purchase line.",
            ("date_from", "date_to", "location", "product", "category", "supplier"),
            build_pending_purchase_stock,
        ),
        Report(
            "pending-purchase-stock-by-location",
            "Pending Purchase Stock by Location",
            "Pending purchase quantities aggregated per location and product.",
            ("date_from", "date_to", "location", "product", "category", "supplier"),
            build_pending_purchase_by_location,
        ),
        Report(
            "in-transit-stock",
            "In-Transit Stock",
            "Shipped but not yet received quantities per shipment line.",
            ("date_from", "date_to", "location", "product", "category", "status"),
            build_in_transit_stock,
        ),
        Report(
            "purchase-report",
            "Purchase Report",
            "Purchase lines with quantities, money, and GST values.",
            ("date_from", "date_to", "location", "product", "category", "supplier", "status"),
            build_purchase_report,
        ),
        Report(
            "party-wise-purchases",
            "Party-wise Purchase Records",
            "Purchase lines grouped by supplier/party.",
            ("date_from", "date_to", "location", "product", "category", "supplier", "status"),
            build_party_wise_purchases,
        ),
        Report(
            "sales-report",
            "Sales Report",
            "Sale lines with reference-only prices.",
            ("date_from", "date_to", "location", "product", "category", "customer"),
            build_sales_report,
        ),
        Report(
            "party-wise-sales",
            "Party-wise Sale Records",
            "Sale lines grouped by customer.",
            ("date_from", "date_to", "location", "product", "category", "customer"),
            build_party_wise_sales,
        ),
        Report(
            "gst-report",
            "GST Report",
            "Product-line GST with net quantities and reversals (SRS §5.1).",
            ("date_from", "date_to", "location", "product", "category", "supplier"),
            build_gst_report,
        ),
        Report(
            "refund-cancellation-report",
            "Refund/Cancellation Report",
            "Refund and cancellation lines with reversed AED/GST values.",
            ("date_from", "date_to", "location", "product", "supplier"),
            build_refund_report,
        ),
        Report(
            "stock-ledger",
            "Stock Ledger Report",
            "Every stock movement, straight from the append-only ledger.",
            ("date_from", "date_to", "location", "product", "category", "bucket", "txn_type"),
            build_stock_ledger_report,
        ),
        Report(
            "stock-adjustments",
            "Stock Adjustment Report",
            "Manual stock corrections with reasons.",
            ("date_from", "date_to", "location", "product", "adjustment_type"),
            build_stock_adjustment_report,
        ),
        Report(
            "user-activity",
            "User Activity Report",
            "Audit trail: who did what, when, from where.",
            ("date_from", "date_to", "user", "action", "module"),
            build_user_activity_report,
        ),
        Report(
            "stock-valuation-summary",
            "Stock Valuation Summary",
            "Total company stock worth by bucket, location, and category (admin only).",
            (*STOCK_FILTERS, "cutoff"),
            build_valuation_summary,
            admin_only=True,
        ),
        Report(
            "stock-valuation-detail",
            "Stock Valuation Detail",
            "Weighted average cost and value per product per location (admin only).",
            (*STOCK_FILTERS, "cutoff"),
            build_valuation_detail,
            admin_only=True,
        ),
    ]
}


def visible_reports(is_admin: bool):
    return [
        report
        for report in REPORTS.values()
        if is_admin or not report.admin_only
    ]


__all__ = [
    "REPORTS",
    "visible_reports",
    "balance_map",
]
