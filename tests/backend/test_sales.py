"""Sale flow tests, keyed to the event→ledger mapping table (§5.2/§13):
sale → −PHYSICAL @ sale location at carrying average; edits post reversal +
fresh rows; deletes post reversal rows only. Every scenario ends with the
balance reconciliation check."""

from decimal import Decimal

import pytest

from apps.accounts.models import User
from apps.audits.models import AuditLog
from apps.inventory.models import Bucket, StockBalance, StockLedgerEntry, TxnType
from apps.inventory.services import rebuild_stock_balances

pytestmark = pytest.mark.django_db

SALES = "/api/v1/sales/"
PURCHASES = "/api/v1/purchases/"


def reconciled():
    return rebuild_stock_balances() == []


def balance(product, location, bucket):
    row = StockBalance.objects.filter(product=product, location=location, bucket=bucket).first()
    return (row.quantity, row.value_aed) if row else (Decimal("0"), Decimal("0"))


@pytest.fixture
def sale_client(auth_client):
    return auth_client(User.Role.SALE)


@pytest.fixture
def customer(db):
    from apps.masterdata.models import Customer

    return Customer.objects.create(name="Walk-in Karachi Trader")


@pytest.fixture
def dubai_stock(auth_client, masterdata):
    """100 units of phone in Dubai physical stock at 120 AED average."""
    client = auth_client(User.Role.PURCHASE)
    response = client.post(
        PURCHASES,
        {
            "invoice_no": "INV-DXB",
            "purchase_date": "2026-07-01",
            "location": masterdata.dubai.pk,
            "supplier": masterdata.supplier.pk,
            "lines": [
                {
                    "product": masterdata.phone.pk,
                    "quantity": "100",
                    "unit_price": "120.00",
                    "currency": masterdata.aed.pk,
                    "collected_qty": "100",
                }
            ],
        },
        format="json",
    )
    assert response.status_code == 201, response.data
    return response.data


def sale_payload(world, customer, **overrides):
    payload = {
        "sale_date": "2026-07-15",
        "location": world.dubai.pk,
        "customer": customer.pk,
        "notes": "",
        "lines": [
            {"product": world.phone.pk, "quantity": "40", "unit_price": "150.00"}
        ],
    }
    payload.update(overrides)
    return payload


class TestSaleEntry:
    def test_sale_reduces_stock_at_carrying_average(
        self, sale_client, masterdata, customer, dubai_stock
    ):
        response = sale_client.post(SALES, sale_payload(masterdata, customer), format="json")
        assert response.status_code == 201, response.data
        assert response.data["sale_no"].startswith("SL-")

        # 40 of 100 @ avg 120 → 4800 AED leaves with the stock; the 150.00
        # sale price is reference-only and never touches stock value.
        assert balance(masterdata.phone, masterdata.dubai, Bucket.PHYSICAL) == (
            Decimal("60.00"), Decimal("7200.00"),
        )
        rows = StockLedgerEntry.objects.filter(txn_type=TxnType.SALE)
        assert rows.count() == 1
        assert rows[0].qty_out == Decimal("40.00")
        assert rows[0].aed_value == Decimal("4800.00")
        assert AuditLog.objects.filter(module="sales", action="CREATE").exists()
        assert reconciled()

    def test_sale_price_optional(self, sale_client, masterdata, customer, dubai_stock):
        payload = sale_payload(masterdata, customer)
        payload["lines"][0].pop("unit_price")
        response = sale_client.post(SALES, payload, format="json")
        assert response.status_code == 201, response.data
        assert response.data["lines"][0]["unit_price"] is None

    def test_non_sales_location_rejected(self, sale_client, masterdata, customer, dubai_stock):
        response = sale_client.post(
            SALES,
            sale_payload(masterdata, customer, location=masterdata.sydney.pk),
            format="json",
        )
        assert response.status_code == 400
        assert "sales location" in str(response.data).lower()

    def test_negative_stock_requires_confirmation(
        self, sale_client, masterdata, customer, dubai_stock
    ):
        payload = sale_payload(masterdata, customer)
        payload["lines"][0]["quantity"] = "150"
        response = sale_client.post(SALES, payload, format="json")
        assert response.status_code == 400
        assert "negative_stock_confirmation_required" in str(response.data)

        response = sale_client.post(f"{SALES}?confirm_negative=true", payload, format="json")
        assert response.status_code == 201, response.data
        assert balance(masterdata.phone, masterdata.dubai, Bucket.PHYSICAL) == (
            Decimal("-50.00"), Decimal("0.00"),
        )
        assert reconciled()

    def test_full_stock_sale_empties_value_exactly(
        self, sale_client, masterdata, customer, dubai_stock
    ):
        payload = sale_payload(masterdata, customer)
        payload["lines"][0]["quantity"] = "100"
        response = sale_client.post(SALES, payload, format="json")
        assert response.status_code == 201, response.data
        assert balance(masterdata.phone, masterdata.dubai, Bucket.PHYSICAL) == (
            Decimal("0.00"), Decimal("0.00"),
        )
        assert reconciled()


class TestSaleEditDelete:
    def _sale(self, client, world, customer):
        response = client.post(SALES, sale_payload(world, customer), format="json")
        assert response.status_code == 201, response.data
        return response.data

    def test_edit_quantity_posts_reversal_and_fresh_rows(
        self, sale_client, masterdata, customer, dubai_stock
    ):
        body = self._sale(sale_client, masterdata, customer)
        payload = sale_payload(masterdata, customer)
        payload["lines"] = [
            {"id": body["lines"][0]["id"], "product": masterdata.phone.pk, "quantity": "10"}
        ]
        response = sale_client.put(f"{SALES}{body['id']}/", payload, format="json")
        assert response.status_code == 200, response.data
        assert response.data["lines"][0]["quantity"] == "10.00"

        # 40 sold then edited to 10 → 90 remain at the original average.
        assert balance(masterdata.phone, masterdata.dubai, Bucket.PHYSICAL) == (
            Decimal("90.00"), Decimal("10800.00"),
        )
        assert StockLedgerEntry.objects.filter(txn_type=TxnType.EDIT_REVERSAL).count() == 2
        assert reconciled()

    def test_price_only_edit_posts_nothing(
        self, sale_client, masterdata, customer, dubai_stock
    ):
        body = self._sale(sale_client, masterdata, customer)
        ledger_before = StockLedgerEntry.objects.count()
        payload = sale_payload(masterdata, customer)
        payload["lines"] = [
            {
                "id": body["lines"][0]["id"],
                "product": masterdata.phone.pk,
                "quantity": "40",
                "unit_price": "175.00",
            }
        ]
        response = sale_client.put(f"{SALES}{body['id']}/", payload, format="json")
        assert response.status_code == 200, response.data
        assert StockLedgerEntry.objects.count() == ledger_before
        assert reconciled()

    def test_location_change_rejected(self, sale_client, masterdata, customer, dubai_stock):
        from apps.masterdata.models import Location

        karachi = Location.objects.create(name="Karachi", is_sales_location=True)
        body = self._sale(sale_client, masterdata, customer)
        payload = sale_payload(masterdata, customer, location=karachi.pk)
        payload["lines"] = [
            {"id": body["lines"][0]["id"], "product": masterdata.phone.pk, "quantity": "40"}
        ]
        response = sale_client.put(f"{SALES}{body['id']}/", payload, format="json")
        assert response.status_code == 400
        assert "location" in str(response.data).lower()

    def test_delete_restores_stock(self, sale_client, masterdata, customer, dubai_stock):
        body = self._sale(sale_client, masterdata, customer)
        response = sale_client.delete(f"{SALES}{body['id']}/")
        assert response.status_code == 204

        assert balance(masterdata.phone, masterdata.dubai, Bucket.PHYSICAL) == (
            Decimal("100.00"), Decimal("12000.00"),
        )
        assert sale_client.get(f"{SALES}{body['id']}/").status_code == 404
        assert AuditLog.objects.filter(module="sales", action="DELETE").exists()
        assert reconciled()


class TestSalePermissionsAndTotals:
    def test_role_matrix(self, auth_client, masterdata, customer, dubai_stock):
        payload = sale_payload(masterdata, customer)
        for role, expected in (
            (User.Role.SALE, 201),
            (User.Role.ADMIN, 201),
            (User.Role.PURCHASE, 403),
            (User.Role.VIEWER, 403),
        ):
            client = auth_client(role)
            assert client.get(SALES).status_code == 200
            response = client.post(SALES, payload, format="json")
            assert response.status_code == expected, (role, response.data)

    def test_sale_user_cannot_create_products(self, sale_client, masterdata):
        response = sale_client.post(
            "/api/v1/products/",
            {"name": "Sneaky Product", "storage_specs": "1TB"},
            format="json",
        )
        assert response.status_code == 403

    def test_list_quick_totals(self, sale_client, masterdata, customer, dubai_stock):
        sale_client.post(SALES, sale_payload(masterdata, customer), format="json")
        response = sale_client.get(SALES)
        assert response.status_code == 200
        assert response.data["totals"]["total_quantity"] == "40.00"
        assert response.data["totals"]["total_sale_value"] == "6000.0000"
