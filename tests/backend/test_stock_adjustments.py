"""Stock adjustment tests (FR-074…FR-077): ±PHYSICAL at carrying average,
mandatory reason, admin-only writes, edit/delete reversals, reconciliation."""

from decimal import Decimal

import pytest

from apps.accounts.models import User
from apps.audits.models import AuditLog
from apps.inventory.models import Bucket, StockBalance, StockLedgerEntry, TxnType
from apps.inventory.services import rebuild_stock_balances

pytestmark = pytest.mark.django_db

ADJUSTMENTS = "/api/v1/stock-adjustments/"
PURCHASES = "/api/v1/purchases/"


def reconciled():
    return rebuild_stock_balances() == []


def balance(product, location, bucket):
    row = StockBalance.objects.filter(product=product, location=location, bucket=bucket).first()
    return (row.quantity, row.value_aed) if row else (Decimal("0"), Decimal("0"))


@pytest.fixture
def sydney_stock(auth_client, masterdata):
    """50 units of phone at Sydney physical, 100 AED average (AED currency)."""
    client = auth_client(User.Role.PURCHASE)
    response = client.post(
        PURCHASES,
        {
            "invoice_no": "INV-ADJ",
            "purchase_date": "2026-07-01",
            "location": masterdata.sydney.pk,
            "supplier": masterdata.supplier.pk,
            "lines": [
                {
                    "product": masterdata.phone.pk,
                    "quantity": "50",
                    "unit_price": "100.00",
                    "currency": masterdata.aed.pk,
                    "collected_qty": "50",
                }
            ],
        },
        format="json",
    )
    assert response.status_code == 201, response.data


def adjustment_payload(world, **overrides):
    payload = {
        "adjustment_date": "2026-07-15",
        "location": world.sydney.pk,
        "product": world.phone.pk,
        "adjustment_type": "DECREASE",
        "quantity": "10",
        "reason": "damaged in storage",
        "notes": "",
    }
    payload.update(overrides)
    return payload


class TestAdjustments:
    def test_decrease_removes_value_at_carrying_average(
        self, admin_client, masterdata, sydney_stock
    ):
        response = admin_client.post(ADJUSTMENTS, adjustment_payload(masterdata), format="json")
        assert response.status_code == 201, response.data

        # Pool: 50 @ 100 = 5000 AED (GST never enters physical stock value).
        assert balance(masterdata.phone, masterdata.sydney, Bucket.PHYSICAL) == (
            Decimal("40.00"), Decimal("4000.00"),
        )
        row = StockLedgerEntry.objects.get(txn_type=TxnType.ADJUSTMENT)
        assert row.qty_out == Decimal("10.00")
        assert AuditLog.objects.filter(module="stock_adjustments", action="CREATE").exists()
        assert reconciled()

    def test_increase_adds_at_carrying_average(self, admin_client, masterdata, sydney_stock):
        response = admin_client.post(
            ADJUSTMENTS,
            adjustment_payload(
                masterdata, adjustment_type="INCREASE", reason="extra stock found"
            ),
            format="json",
        )
        assert response.status_code == 201, response.data
        # Unit cost is undisturbed: 60 @ 100 average.
        assert balance(masterdata.phone, masterdata.sydney, Bucket.PHYSICAL) == (
            Decimal("60.00"), Decimal("6000.00"),
        )
        assert reconciled()

    def test_reason_required(self, admin_client, masterdata, sydney_stock):
        response = admin_client.post(
            ADJUSTMENTS, adjustment_payload(masterdata, reason="  "), format="json"
        )
        assert response.status_code == 400
        assert "reason" in str(response.data).lower()

    def test_negative_stock_requires_confirmation(self, admin_client, masterdata, sydney_stock):
        payload = adjustment_payload(masterdata, quantity="80")
        response = admin_client.post(ADJUSTMENTS, payload, format="json")
        assert response.status_code == 400
        assert "negative_stock_confirmation_required" in str(response.data)

        response = admin_client.post(
            f"{ADJUSTMENTS}?confirm_negative=true", payload, format="json"
        )
        assert response.status_code == 201, response.data
        assert reconciled()

    def test_edit_posts_reversal_and_fresh_rows(self, admin_client, masterdata, sydney_stock):
        body = admin_client.post(
            ADJUSTMENTS, adjustment_payload(masterdata), format="json"
        ).data
        payload = adjustment_payload(masterdata, quantity="5")
        response = admin_client.put(f"{ADJUSTMENTS}{body['id']}/", payload, format="json")
        assert response.status_code == 200, response.data

        # Net effect is now −5 of 50 @ 100 → 45 remain worth 4500.
        assert balance(masterdata.phone, masterdata.sydney, Bucket.PHYSICAL) == (
            Decimal("45.00"), Decimal("4500.00"),
        )
        assert StockLedgerEntry.objects.filter(txn_type=TxnType.EDIT_REVERSAL).count() == 2
        assert reconciled()

    def test_delete_reverses_adjustment(self, admin_client, masterdata, sydney_stock):
        body = admin_client.post(
            ADJUSTMENTS, adjustment_payload(masterdata), format="json"
        ).data
        response = admin_client.delete(f"{ADJUSTMENTS}{body['id']}/")
        assert response.status_code == 204

        assert balance(masterdata.phone, masterdata.sydney, Bucket.PHYSICAL) == (
            Decimal("50.00"), Decimal("5000.00"),
        )
        assert admin_client.get(f"{ADJUSTMENTS}{body['id']}/").status_code == 404
        assert reconciled()

    def test_admin_only_writes(self, auth_client, masterdata, sydney_stock):
        payload = adjustment_payload(masterdata)
        for role in (User.Role.PURCHASE, User.Role.SALE, User.Role.VIEWER):
            client = auth_client(role)
            assert client.get(ADJUSTMENTS).status_code == 200
            assert client.post(ADJUSTMENTS, payload, format="json").status_code == 403
