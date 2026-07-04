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
    help = "Seed demo master data (idempotent). Adds a dev admin user when DEBUG."

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
