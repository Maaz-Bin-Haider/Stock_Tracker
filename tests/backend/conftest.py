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
