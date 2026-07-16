"""Idempotent dev seed: locations, currencies, GST/exchange rates, categories,
and (DEBUG only) a default admin user. TECHNICAL_ARCHITECTURE §11 (`make seed`).
"""

import datetime
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.masterdata.models import Category, Currency, ExchangeRate, GstRate, Location

LOCATIONS = [
    # name, country, city, sales, region_group, gst_region
    ("Sydney", "Australia", "Sydney", False, "AU", "AU"),
    ("Melbourne", "Australia", "Melbourne", False, "AU", "AU"),
    ("Perth", "Australia", "Perth", False, "AU", "AU"),
    ("New Zealand", "New Zealand", "", False, "NZ", "NZ"),
    ("Dubai", "UAE", "Dubai", True, "", ""),
    ("Houston", "USA", "Houston", False, "US", ""),
    ("Karachi", "Pakistan", "Karachi", True, "", ""),
]

CURRENCIES = [
    ("AED", "UAE Dirham"),
    ("AUD", "Australian Dollar"),
    ("NZD", "New Zealand Dollar"),
    ("USD", "US Dollar"),
    ("PKR", "Pakistani Rupee"),
]

# Dev placeholder rates; real rates are maintained in Settings (FR-088).
EXCHANGE_RATES = {
    "AED": Decimal("1.000000"),
    "AUD": Decimal("2.400000"),
    "NZD": Decimal("2.200000"),
    "USD": Decimal("3.672500"),
    "PKR": Decimal("0.013000"),
}

GST_RATES = {"AU": Decimal("10.00"), "NZ": Decimal("15.00")}

CATEGORIES = ["iPhone", "MacBook", "Starlink", "JBL", "Camera", "Accessories"]


class Command(BaseCommand):
    help = (
        "Seed demo master data (idempotent). Adds a dev admin user when DEBUG. "
        "--demo also builds a small business history (purchases, collection, "
        "refund, shipments, sales, adjustment) through the domain services."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--demo",
            action="store_true",
            help="Also create demo business flows (skipped if already present).",
        )

    def handle(self, *args, **options):
        for name, country, city, sales, region, gst_region in LOCATIONS:
            Location.objects.get_or_create(
                name=name,
                defaults={
                    "country": country,
                    "city": city,
                    "can_purchase": True,
                    "is_sales_location": sales,
                    "region_group": region,
                    "gst_region": gst_region,
                },
            )

        for code, name in CURRENCIES:
            currency, _ = Currency.objects.get_or_create(code=code, defaults={"name": name})
            ExchangeRate.objects.get_or_create(
                currency=currency,
                effective_date=datetime.date(2026, 1, 1),
                defaults={"rate_to_aed": EXCHANGE_RATES[code]},
            )

        for gst_region, rate in GST_RATES.items():
            for location in Location.objects.filter(gst_region=gst_region):
                GstRate.objects.get_or_create(
                    location=location,
                    effective_from=datetime.date(2026, 1, 1),
                    defaults={"rate": rate},
                )

        for name in CATEGORIES:
            Category.objects.get_or_create(name=name)

        if settings.DEBUG:
            user_model = get_user_model()
            if not user_model.objects.filter(username="admin").exists():
                user_model.objects.create_superuser(
                    "admin", "admin@example.com", "admin123", role=user_model.Role.ADMIN
                )
                self.stdout.write("Created dev admin user: admin / admin123 (DEBUG only)")

        self.stdout.write(self.style.SUCCESS("Master data seeded."))

        if options["demo"]:
            self._seed_demo_flows()

    def _seed_demo_flows(self):
        """A believable little history so the dashboard, reports, valuation,
        and exports have data to show on a fresh environment (M7 seed pass).
        Everything goes through the domain services, so ledger, balances, and
        audit rows are exactly what real usage would produce. Runs in one
        transaction: either the whole history lands or none of it."""
        from django.db import transaction

        from apps.purchases.models import Purchase

        if Purchase.objects.filter(invoice_no="DEMO-0001", is_deleted=False).exists():
            self.stdout.write("Demo flows already present; skipping.")
            return
        transaction.atomic(self._run_demo_flows)()

    def _run_demo_flows(self):
        from apps.core.time import business_today
        from apps.inventory.adjustments import create_adjustment
        from apps.masterdata.models import Customer, Supplier
        from apps.products.models import Product
        from apps.purchases.services import collect_purchase, create_purchase, create_refund
        from apps.sales.services import create_sale
        from apps.shipments.services import create_shipment, receive_shipment

        user_model = get_user_model()
        admin = user_model.objects.filter(role=user_model.Role.ADMIN).first()
        if admin is None:
            self.stdout.write(self.style.WARNING("No admin user; skipping demo flows."))
            return

        sydney = Location.objects.get(name="Sydney")
        dubai = Location.objects.get(name="Dubai")
        karachi = Location.objects.get(name="Karachi")
        aed = Currency.objects.get(code="AED")
        aud = Currency.objects.get(code="AUD")
        iphone_cat = Category.objects.get(name="iPhone")
        macbook_cat = Category.objects.get(name="MacBook")

        supplier_syd, _ = Supplier.objects.get_or_create(
            name="Sydney Wholesale Traders", defaults={"country": "Australia", "city": "Sydney"}
        )
        supplier_dxb, _ = Supplier.objects.get_or_create(
            name="Dubai Electronics Market", defaults={"country": "UAE", "city": "Dubai"}
        )
        customer_dxb, _ = Customer.objects.get_or_create(
            name="Al Noor Mobiles", defaults={"country": "UAE", "city": "Dubai"}
        )
        customer_khi, _ = Customer.objects.get_or_create(
            name="Karachi Tech House", defaults={"country": "Pakistan", "city": "Karachi"}
        )

        phone, _ = Product.objects.get_or_create(
            name="iPhone 16 Pro", storage_specs="256GB", defaults={"category": iphone_cat}
        )
        laptop, _ = Product.objects.get_or_create(
            name="MacBook Air M4", storage_specs="16GB/512GB", defaults={"category": macbook_cat}
        )

        today = business_today()
        rate_aud = EXCHANGE_RATES["AUD"]

        # Sydney AUD purchase with GST: 20 phones, 15 collected.
        p1 = create_purchase(
            header={
                "invoice_no": "DEMO-0001",
                "purchase_date": today - datetime.timedelta(days=14),
                "location": sydney,
                "supplier": supplier_syd,
                "notes": "Demo data.",
            },
            lines=[
                {
                    "product": phone,
                    "quantity": Decimal("20"),
                    "unit_price": Decimal("1500.00"),
                    "currency": aud,
                    "exchange_rate": rate_aud,
                    "gst_rate_percent": GST_RATES["AU"],
                    "collected_qty": Decimal("15"),
                }
            ],
            user=admin,
        )
        # Cancel 2 undelivered units (reverses stock + GST).
        create_refund(
            purchase=p1,
            refund_date=today - datetime.timedelta(days=10),
            reason="Supplier short-shipped the order.",
            lines=[
                {
                    "purchase_line": p1.lines.first(),
                    "source": "PENDING",
                    "quantity": Decimal("2"),
                }
            ],
            user=admin,
        )

        # Dubai AED purchase: 30 laptops fully collected.
        create_purchase(
            header={
                "invoice_no": "DEMO-0002",
                "purchase_date": today - datetime.timedelta(days=12),
                "location": dubai,
                "supplier": supplier_dxb,
                "notes": "Demo data.",
            },
            lines=[
                {
                    "product": laptop,
                    "quantity": Decimal("30"),
                    "unit_price": Decimal("3200.00"),
                    "currency": aed,
                    "exchange_rate": Decimal("1.000000"),
                    "gst_rate_percent": Decimal("0.00"),
                    "collected_qty": Decimal("30"),
                }
            ],
            user=admin,
        )
        collect_purchase(
            purchase=p1,
            collection_date=today - datetime.timedelta(days=9),
            location=sydney,
            lines=[{"purchase_line": p1.lines.first(), "quantity": Decimal("3")}],
            notes="Second pickup.",
            user=admin,
        )

        # Sydney → Dubai shipment, partially received; Dubai → Karachi transfer.
        s1 = create_shipment(
            header={
                "shipment_date": today - datetime.timedelta(days=7),
                "from_location": sydney,
                "to_location": dubai,
                "shipment_type": "STANDARD",
                "shipping_cost": Decimal("450.00"),
                "notes": "Demo data.",
            },
            lines=[{"product": phone, "quantity": Decimal("12")}],
            ship=True,
            user=admin,
        )
        receive_shipment(
            shipment=s1,
            receipt_date=today - datetime.timedelta(days=4),
            lines=[{"shipment_line": s1.lines.first(), "quantity": Decimal("10")}],
            user=admin,
        )
        s2 = create_shipment(
            header={
                "shipment_date": today - datetime.timedelta(days=3),
                "from_location": dubai,
                "to_location": karachi,
                "shipment_type": "DUBAI_KARACHI",
                "shipping_cost": Decimal("120.00"),
                "notes": "Demo data.",
            },
            lines=[{"product": phone, "quantity": Decimal("4")}],
            ship=True,
            user=admin,
        )
        receive_shipment(
            shipment=s2,
            receipt_date=today - datetime.timedelta(days=1),
            lines=[{"shipment_line": s2.lines.first(), "quantity": Decimal("4")}],
            user=admin,
        )

        # Sales: history + today (drives the "today's sales" card).
        create_sale(
            header={
                "sale_date": today - datetime.timedelta(days=2),
                "location": dubai,
                "customer": customer_dxb,
                "notes": "Demo data.",
            },
            lines=[
                {"product": laptop, "quantity": Decimal("5"), "unit_price": Decimal("3600.00")}
            ],
            user=admin,
        )
        create_sale(
            header={
                "sale_date": today,
                "location": karachi,
                "customer": customer_khi,
                "notes": "Demo data.",
            },
            lines=[{"product": phone, "quantity": Decimal("2")}],
            user=admin,
        )
        create_sale(
            header={
                "sale_date": today,
                "location": dubai,
                "customer": customer_dxb,
                "notes": "Demo data.",
            },
            lines=[
                {"product": phone, "quantity": Decimal("3"), "unit_price": Decimal("4100.00")}
            ],
            user=admin,
        )

        # Count correction so the adjustment report has a row.
        create_adjustment(
            data={
                "adjustment_date": today - datetime.timedelta(days=1),
                "location": dubai,
                "product": laptop,
                "adjustment_type": "INCREASE",
                "quantity": Decimal("1"),
                "reason": "Demo count correction — extra unit found.",
                "notes": "Demo data.",
            },
            user=admin,
        )

        self.stdout.write(self.style.SUCCESS("Demo business flows seeded."))
