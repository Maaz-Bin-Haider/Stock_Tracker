import datetime
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User

PASSWORD = "pass12345"


@pytest.fixture
def make_user(db):
    def _make(role, username=None, **kwargs):
        username = username or f"{role.lower()}_user"
        existing = User.objects.filter(username=username).first()
        if existing is not None:
            return existing
        return User.objects.create_user(
            username=username, password=PASSWORD, role=role, **kwargs
        )

    return _make


@pytest.fixture
def auth_client(make_user):
    """APIClient logged in through a real session, so audit rows attribute
    to the user exactly as they do in production."""

    def _client(role):
        user = make_user(role)
        client = APIClient()
        assert client.login(username=user.username, password=PASSWORD)
        client.user = user
        return client

    return _client


@pytest.fixture
def admin_client(auth_client):
    return auth_client(User.Role.ADMIN)


@pytest.fixture
def masterdata(db):
    """Minimal business world for stock-flow tests: locations, AUD/AED with
    rates, an AU GST rate, a category, products, and a supplier."""
    from apps.masterdata.models import (
        Category,
        Currency,
        ExchangeRate,
        GstRate,
        Location,
        Supplier,
    )
    from apps.products.models import Product

    sydney = Location.objects.create(
        name="Sydney", country="Australia", region_group="AU", gst_region="AU"
    )
    dubai = Location.objects.create(name="Dubai", country="UAE", is_sales_location=True)
    aed = Currency.objects.create(code="AED")
    aud = Currency.objects.create(code="AUD")
    ExchangeRate.objects.create(
        currency=aed, rate_to_aed=Decimal("1.000000"), effective_date=datetime.date(2026, 1, 1)
    )
    ExchangeRate.objects.create(
        currency=aud, rate_to_aed=Decimal("2.400000"), effective_date=datetime.date(2026, 1, 1)
    )
    gst_au = GstRate.objects.create(
        location=sydney, rate=Decimal("10.00"), effective_from=datetime.date(2026, 1, 1)
    )
    category = Category.objects.create(name="iPhone")
    phone = Product.objects.create(name="iPhone 15 Pro", storage_specs="256GB", category=category)
    laptop = Product.objects.create(name="MacBook Air", storage_specs="M3", category=category)
    supplier = Supplier.objects.create(name="Apple Distributor Sydney")

    class World:
        pass

    world = World()
    world.sydney, world.dubai = sydney, dubai
    world.aed, world.aud = aed, aud
    world.gst_au = gst_au
    world.phone, world.laptop = phone, laptop
    world.supplier = supplier
    return world


@pytest.fixture
def report_world(masterdata, auth_client):
    """A small business history exercising every report source (M6 tests):

    - P1 Sydney: 10 phone @ 100 AUD (fx 2.4 → 240 AED, GST 10%), 6 collected,
      2 pending cancelled, 1 received refunded → pending 2 (480 AED / 48 GST),
      Sydney physical 5 (1200 AED) before shipping.
    - P2 Dubai: 20 laptop @ 50 AED fully collected → 20 (1000 AED).
    - S1 Sydney→Dubai: 3 phone shipped, 2 received → Sydney physical 2,
      Dubai physical 2, in-transit 1 (240 AED).
    - SL1 Dubai today: 2 laptop; SL2 Dubai 2026-07-14: 1 laptop.
    - A1 Dubai: +1 laptop (admin adjustment) → laptop physical 18 (900 AED).

    ``world.mid_cutoff`` is a timestamp taken after the purchases/refunds but
    before the shipment/sales/adjustment, for past-snapshot assertions.
    """
    from django.utils import timezone

    from apps.core.time import business_today

    world = masterdata
    purchase = auth_client(User.Role.PURCHASE)
    sale = auth_client(User.Role.SALE)
    admin = auth_client(User.Role.ADMIN)

    p1 = purchase.post(
        "/api/v1/purchases/",
        {
            "invoice_no": "INV-P1",
            "purchase_date": "2026-07-01",
            "location": world.sydney.pk,
            "supplier": world.supplier.pk,
            "lines": [
                {
                    "product": world.phone.pk,
                    "quantity": "10",
                    "unit_price": "100.00",
                    "currency": world.aud.pk,
                    "collected_qty": "6",
                }
            ],
        },
        format="json",
    )
    assert p1.status_code == 201, p1.data
    p1_line = p1.data["lines"][0]["id"]

    for source, quantity, date in (("PENDING", "2", "2026-07-05"), ("RECEIVED", "1", "2026-07-06")):
        refund = purchase.post(
            f"/api/v1/purchases/{p1.data['id']}/refunds/",
            {
                "refund_date": date,
                "reason": "Report world refund.",
                "lines": [{"purchase_line": p1_line, "source": source, "quantity": quantity}],
            },
            format="json",
        )
        assert refund.status_code == 201, refund.data

    p2 = purchase.post(
        "/api/v1/purchases/",
        {
            "invoice_no": "INV-P2",
            "purchase_date": "2026-07-02",
            "location": world.dubai.pk,
            "supplier": world.supplier.pk,
            "lines": [
                {
                    "product": world.laptop.pk,
                    "quantity": "20",
                    "unit_price": "50.00",
                    "currency": world.aed.pk,
                    "collected_qty": "20",
                }
            ],
        },
        format="json",
    )
    assert p2.status_code == 201, p2.data

    world.mid_cutoff = timezone.now()

    shipment = purchase.post(
        "/api/v1/shipments/",
        {
            "shipment_date": "2026-07-10",
            "from_location": world.sydney.pk,
            "to_location": world.dubai.pk,
            "shipment_type": "STANDARD",
            "shipping_cost": "100.00",
            "ship": True,
            "lines": [{"product": world.phone.pk, "quantity": "3"}],
        },
        format="json",
    )
    assert shipment.status_code == 201, shipment.data
    receipt = purchase.post(
        f"/api/v1/shipments/{shipment.data['id']}/receipts/",
        {
            "receipt_date": "2026-07-12",
            "lines": [{"shipment_line": shipment.data["lines"][0]["id"], "quantity": "2"}],
        },
        format="json",
    )
    assert receipt.status_code == 201, receipt.data

    from apps.masterdata.models import Customer

    customer = Customer.objects.create(name="Report Customer")
    world.today = business_today()
    for sale_date, quantity, price in ((str(world.today), "2", "80.00"), ("2026-07-14", "1", None)):
        line = {"product": world.laptop.pk, "quantity": quantity}
        if price:
            line["unit_price"] = price
        response = sale.post(
            "/api/v1/sales/",
            {
                "sale_date": sale_date,
                "location": world.dubai.pk,
                "customer": customer.pk,
                "lines": [line],
            },
            format="json",
        )
        assert response.status_code == 201, response.data

    adjustment = admin.post(
        "/api/v1/stock-adjustments/",
        {
            "adjustment_date": "2026-07-15",
            "location": world.dubai.pk,
            "product": world.laptop.pk,
            "adjustment_type": "INCREASE",
            "quantity": "1",
            "reason": "Extra unit found in count.",
        },
        format="json",
    )
    assert adjustment.status_code == 201, adjustment.data

    world.customer = customer
    world.purchase_client = purchase
    world.sale_client = sale
    world.admin_client = admin
    world.p1, world.p2, world.shipment = p1.data, p2.data, shipment.data
    return world
