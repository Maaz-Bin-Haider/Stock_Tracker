"""Purchase refund/cancellation tests (M3), keyed to the §5.2 mapping rows:
refund/cancel of pending qty → −PENDING; refund of received qty → −PHYSICAL
with AED/GST reversed at the original purchase line rate. Every scenario ends
with the ledger reconciliation check."""

from decimal import Decimal

import pytest

from apps.accounts.models import User
from apps.audits.models import AuditLog
from apps.inventory.models import Bucket, StockBalance, StockLedgerEntry, TxnType
from apps.inventory.services import rebuild_stock_balances
from apps.purchases.models import Purchase, PurchaseStatus

pytestmark = pytest.mark.django_db

PURCHASES = "/api/v1/purchases/"


def reconciled():
    return rebuild_stock_balances() == []


def balance(product, location, bucket):
    row = StockBalance.objects.filter(product=product, location=location, bucket=bucket).first()
    return (row.quantity, row.value_aed) if row else (Decimal("0"), Decimal("0"))


@pytest.fixture
def purchase_client(auth_client):
    return auth_client(User.Role.PURCHASE)


@pytest.fixture
def invoice(purchase_client, masterdata):
    """INV-001: 100 phones @ 1500 AUD (fx 2.4, GST 10%), 70 collected."""
    response = purchase_client.post(
        PURCHASES,
        {
            "invoice_no": "INV-001",
            "purchase_date": "2026-07-01",
            "location": masterdata.sydney.pk,
            "supplier": masterdata.supplier.pk,
            "lines": [
                {
                    "product": masterdata.phone.pk,
                    "quantity": "100",
                    "unit_price": "1500.00",
                    "currency": masterdata.aud.pk,
                    "collected_qty": "70",
                }
            ],
        },
        format="json",
    )
    assert response.status_code == 201, response.data
    return response.data


def refund_payload(line_id, source, quantity, **extra):
    return {
        "refund_date": "2026-07-05",
        "reason": "Supplier cancelled the remainder.",
        "lines": [{"purchase_line": line_id, "source": source, "quantity": quantity}],
        **extra,
    }


class TestPendingCancellation:
    def test_cancel_pending_reverses_pending_and_gst(
        self, purchase_client, masterdata, invoice
    ):
        line_id = invoice["lines"][0]["id"]
        response = purchase_client.post(
            f"{PURCHASES}{invoice['id']}/refunds/",
            refund_payload(line_id, "PENDING", "30"),
            format="json",
        )
        assert response.status_code == 201, response.data
        refund_line = response.data["lines"][0]
        # Original line rate: 30 × 1500 AUD = 45000 AUD → 108000 AED; GST 10%.
        assert refund_line["value_reversal"] == "45000.00"
        assert refund_line["value_reversal_aed"] == "108000.00"
        assert refund_line["gst_reversal"] == "4500.00"
        assert refund_line["gst_reversal_aed"] == "10800.00"
        assert response.data["refund_no"].startswith("RF-")

        # Pending empties exactly: qty 100 − 70 collected − 30 cancelled = 0.
        assert balance(masterdata.phone, masterdata.sydney, Bucket.PENDING) == (
            Decimal("0.00"),
            Decimal("0.00"),
        )
        # Physical stock untouched by a pending cancellation.
        assert balance(masterdata.phone, masterdata.sydney, Bucket.PHYSICAL) == (
            Decimal("70.00"),
            Decimal("252000.00"),
        )
        entry = StockLedgerEntry.objects.get(txn_type=TxnType.PURCHASE_REFUND)
        assert entry.bucket == Bucket.PENDING
        assert entry.qty_out == Decimal("30.00")
        assert entry.gst_value == Decimal("10800.00")

        purchase = Purchase.objects.get(pk=invoice["id"])
        line = purchase.lines.get()
        assert line.pending_qty == Decimal("0.00")
        assert line.net_qty == Decimal("70.00")
        assert line.status == PurchaseStatus.FULLY_COLLECTED
        assert AuditLog.objects.filter(module="purchase_refunds", action="CREATE").exists()
        assert reconciled()

    def test_cancel_more_than_pending_rejected(self, purchase_client, masterdata, invoice):
        line_id = invoice["lines"][0]["id"]
        response = purchase_client.post(
            f"{PURCHASES}{invoice['id']}/refunds/",
            refund_payload(line_id, "PENDING", "31"),
            format="json",
        )
        assert response.status_code == 400
        assert StockLedgerEntry.objects.filter(txn_type=TxnType.PURCHASE_REFUND).count() == 0
        assert reconciled()

    def test_cancel_everything_on_uncollected_line(self, purchase_client, masterdata):
        response = purchase_client.post(
            PURCHASES,
            {
                "invoice_no": "INV-002",
                "purchase_date": "2026-07-01",
                "location": masterdata.sydney.pk,
                "supplier": masterdata.supplier.pk,
                "lines": [
                    {
                        "product": masterdata.laptop.pk,
                        "quantity": "10",
                        "unit_price": "2000.00",
                        "currency": masterdata.aud.pk,
                    }
                ],
            },
            format="json",
        )
        body = response.data
        response = purchase_client.post(
            f"{PURCHASES}{body['id']}/refunds/",
            refund_payload(body["lines"][0]["id"], "PENDING", "10"),
            format="json",
        )
        assert response.status_code == 201, response.data
        purchase = Purchase.objects.get(pk=body["id"])
        assert purchase.lines.get().status == PurchaseStatus.CANCELLED
        assert purchase.status == PurchaseStatus.CANCELLED
        assert balance(masterdata.laptop, masterdata.sydney, Bucket.PENDING) == (
            Decimal("0.00"),
            Decimal("0.00"),
        )
        assert reconciled()


class TestReceivedRefund:
    def test_refund_received_reverses_physical_at_line_rate(
        self, purchase_client, masterdata, invoice
    ):
        line_id = invoice["lines"][0]["id"]
        response = purchase_client.post(
            f"{PURCHASES}{invoice['id']}/refunds/",
            refund_payload(line_id, "RECEIVED", "20"),
            format="json",
        )
        assert response.status_code == 201, response.data
        refund_line = response.data["lines"][0]
        assert refund_line["value_reversal_aed"] == "72000.00"  # 20 × 3600
        assert refund_line["gst_reversal_aed"] == "7200.00"

        assert balance(masterdata.phone, masterdata.sydney, Bucket.PHYSICAL) == (
            Decimal("50.00"),
            Decimal("180000.00"),
        )
        # Pending untouched by a received refund.
        assert balance(masterdata.phone, masterdata.sydney, Bucket.PENDING) == (
            Decimal("30.00"),
            Decimal("108000.00"),
        )
        entry = StockLedgerEntry.objects.get(txn_type=TxnType.PURCHASE_REFUND)
        assert entry.bucket == Bucket.PHYSICAL
        assert entry.location == masterdata.sydney

        line = Purchase.objects.get(pk=invoice["id"]).lines.get()
        assert line.net_qty == Decimal("80.00")
        assert line.pending_qty == Decimal("30.00")
        assert line.status == PurchaseStatus.PARTIALLY_RECEIVED
        assert reconciled()

    def test_refund_more_than_in_stock_rejected(self, purchase_client, masterdata, invoice):
        line_id = invoice["lines"][0]["id"]
        response = purchase_client.post(
            f"{PURCHASES}{invoice['id']}/refunds/",
            refund_payload(line_id, "RECEIVED", "71"),
            format="json",
        )
        assert response.status_code == 400
        assert reconciled()

    def test_refund_whole_line_marks_refunded(self, purchase_client, masterdata, invoice):
        line_id = invoice["lines"][0]["id"]
        purchase_client.post(
            f"{PURCHASES}{invoice['id']}/refunds/",
            refund_payload(line_id, "PENDING", "30"),
            format="json",
        )
        response = purchase_client.post(
            f"{PURCHASES}{invoice['id']}/refunds/",
            refund_payload(line_id, "RECEIVED", "70"),
            format="json",
        )
        assert response.status_code == 201, response.data
        purchase = Purchase.objects.get(pk=invoice["id"])
        line = purchase.lines.get()
        assert line.status == PurchaseStatus.REFUNDED
        assert line.net_qty == Decimal("0.00")
        assert purchase.status == PurchaseStatus.REFUNDED
        for bucket in (Bucket.PENDING, Bucket.PHYSICAL):
            assert balance(masterdata.phone, masterdata.sydney, bucket) == (
                Decimal("0.00"),
                Decimal("0.00"),
            )
        assert reconciled()

    def test_mixed_lines_one_invoice(self, purchase_client, masterdata):
        """SYSTEM_SPEC §10: in one invoice some products received, others
        pending; both refundable/cancellable independently."""
        response = purchase_client.post(
            PURCHASES,
            {
                "invoice_no": "INV-003",
                "purchase_date": "2026-07-01",
                "location": masterdata.sydney.pk,
                "supplier": masterdata.supplier.pk,
                "lines": [
                    {
                        "product": masterdata.phone.pk,
                        "quantity": "10",
                        "unit_price": "1500.00",
                        "currency": masterdata.aud.pk,
                        "collected_qty": "10",
                    },
                    {
                        "product": masterdata.laptop.pk,
                        "quantity": "5",
                        "unit_price": "2000.00",
                        "currency": masterdata.aud.pk,
                    },
                ],
            },
            format="json",
        )
        body = response.data
        response = purchase_client.post(
            f"{PURCHASES}{body['id']}/refunds/",
            {
                "refund_date": "2026-07-05",
                "reason": "Return phones, cancel laptops.",
                "lines": [
                    {
                        "purchase_line": body["lines"][0]["id"],
                        "source": "RECEIVED",
                        "quantity": "4",
                    },
                    {
                        "purchase_line": body["lines"][1]["id"],
                        "source": "PENDING",
                        "quantity": "5",
                    },
                ],
            },
            format="json",
        )
        assert response.status_code == 201, response.data
        purchase = Purchase.objects.get(pk=body["id"])
        phone_line = purchase.lines.get(product=masterdata.phone)
        laptop_line = purchase.lines.get(product=masterdata.laptop)
        assert phone_line.net_qty == Decimal("6.00")
        assert phone_line.status == PurchaseStatus.FULLY_COLLECTED
        assert laptop_line.status == PurchaseStatus.CANCELLED
        assert balance(masterdata.phone, masterdata.sydney, Bucket.PHYSICAL)[0] == Decimal("6.00")
        assert balance(masterdata.laptop, masterdata.sydney, Bucket.PENDING)[0] == Decimal("0.00")
        assert reconciled()


class TestRefundLifecycle:
    def test_reason_required(self, purchase_client, masterdata, invoice):
        payload = refund_payload(invoice["lines"][0]["id"], "PENDING", "10", reason="  ")
        response = purchase_client.post(
            f"{PURCHASES}{invoice['id']}/refunds/", payload, format="json"
        )
        assert response.status_code == 400

    def test_delete_refund_restores_state(self, purchase_client, masterdata, invoice):
        line_id = invoice["lines"][0]["id"]
        response = purchase_client.post(
            f"{PURCHASES}{invoice['id']}/refunds/",
            refund_payload(line_id, "PENDING", "30"),
            format="json",
        )
        refund_id = response.data["id"]
        response = purchase_client.delete(f"{PURCHASES}{invoice['id']}/refunds/{refund_id}/")
        assert response.status_code == 204
        assert balance(masterdata.phone, masterdata.sydney, Bucket.PENDING) == (
            Decimal("30.00"),
            Decimal("108000.00"),
        )
        line = Purchase.objects.get(pk=invoice["id"]).lines.get()
        assert line.pending_qty == Decimal("30.00")
        assert line.refunded_qty == Decimal("0.00")
        assert purchase_client.get(f"{PURCHASES}{invoice['id']}/refunds/").data == []
        assert reconciled()

    def test_collect_again_after_partial_cancel(self, purchase_client, masterdata, invoice):
        """Cancel 10 of the 30 pending, then collect the remaining 20."""
        line_id = invoice["lines"][0]["id"]
        purchase_client.post(
            f"{PURCHASES}{invoice['id']}/refunds/",
            refund_payload(line_id, "PENDING", "10"),
            format="json",
        )
        response = purchase_client.post(
            f"{PURCHASES}{invoice['id']}/collections/",
            {
                "collection_date": "2026-07-06",
                "lines": [{"purchase_line": line_id, "quantity": "20"}],
            },
            format="json",
        )
        assert response.status_code == 201, response.data
        assert balance(masterdata.phone, masterdata.sydney, Bucket.PENDING) == (
            Decimal("0.00"),
            Decimal("0.00"),
        )
        assert balance(masterdata.phone, masterdata.sydney, Bucket.PHYSICAL)[0] == Decimal(
            "90.00"
        )
        line = Purchase.objects.get(pk=invoice["id"]).lines.get()
        assert line.status == PurchaseStatus.FULLY_COLLECTED
        assert reconciled()

    def test_edit_quantity_floor_includes_cancelled(self, purchase_client, masterdata, invoice):
        """After collecting 70 and cancelling 10, quantity cannot drop below 80."""
        line_id = invoice["lines"][0]["id"]
        purchase_client.post(
            f"{PURCHASES}{invoice['id']}/refunds/",
            refund_payload(line_id, "PENDING", "10"),
            format="json",
        )
        line = invoice["lines"][0]
        payload = {
            "invoice_no": invoice["invoice_no"],
            "purchase_date": invoice["purchase_date"],
            "location": invoice["location"],
            "supplier": invoice["supplier"],
            "notes": "",
            "lines": [
                {
                    "id": line_id,
                    "product": line["product"],
                    "quantity": "75",
                    "unit_price": line["unit_price"],
                    "currency": line["currency"],
                    "exchange_rate": line["exchange_rate"],
                    "gst_rate_percent": line["gst_rate_percent"],
                }
            ],
        }
        response = purchase_client.put(
            f"{PURCHASES}{invoice['id']}/", payload, format="json"
        )
        assert response.status_code == 400

        payload["lines"][0]["quantity"] = "90"
        response = purchase_client.put(
            f"{PURCHASES}{invoice['id']}/", payload, format="json"
        )
        assert response.status_code == 200, response.data
        # 90 total − 70 collected − 10 cancelled = 10 pending.
        assert balance(masterdata.phone, masterdata.sydney, Bucket.PENDING)[0] == Decimal(
            "10.00"
        )
        assert reconciled()

    def test_delete_purchase_after_received_refund(self, purchase_client, masterdata, invoice):
        """Refund drains part of physical; purchase delete must reverse only
        what remains (no over-reversal)."""
        line_id = invoice["lines"][0]["id"]
        purchase_client.post(
            f"{PURCHASES}{invoice['id']}/refunds/",
            refund_payload(line_id, "RECEIVED", "20"),
            format="json",
        )
        response = purchase_client.delete(f"{PURCHASES}{invoice['id']}/")
        assert response.status_code == 204
        for bucket in (Bucket.PENDING, Bucket.PHYSICAL):
            assert balance(masterdata.phone, masterdata.sydney, bucket) == (
                Decimal("0.00"),
                Decimal("0.00"),
            )
        assert reconciled()


class TestRefundPermissions:
    @pytest.mark.parametrize(
        "role,expected",
        [
            (User.Role.ADMIN, 201),
            (User.Role.PURCHASE, 201),
            (User.Role.SALE, 403),
            (User.Role.VIEWER, 403),
        ],
    )
    def test_create_by_role(self, auth_client, purchase_client, masterdata, invoice, role, expected):
        client = purchase_client if role == User.Role.PURCHASE else auth_client(role)
        response = client.post(
            f"{PURCHASES}{invoice['id']}/refunds/",
            refund_payload(invoice["lines"][0]["id"], "PENDING", "5"),
            format="json",
        )
        assert response.status_code == expected

    def test_all_roles_can_list_refunds(self, auth_client, purchase_client, masterdata, invoice):
        purchase_client.post(
            f"{PURCHASES}{invoice['id']}/refunds/",
            refund_payload(invoice["lines"][0]["id"], "PENDING", "5"),
            format="json",
        )
        for role in (User.Role.SALE, User.Role.VIEWER):
            response = auth_client(role).get(f"{PURCHASES}{invoice['id']}/refunds/")
            assert response.status_code == 200
            assert len(response.data) == 1
