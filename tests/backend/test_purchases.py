"""Purchase → pending → collect flow tests, keyed to the event→ledger mapping
table (TECHNICAL_ARCHITECTURE §5.2/§13). Every scenario ends with the balance
reconciliation check: rebuild_stock_balances must report zero drift."""

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


def invoice_payload(world, **overrides):
    payload = {
        "invoice_no": "INV-001",
        "purchase_date": "2026-07-01",
        "location": world.sydney.pk,
        "supplier": world.supplier.pk,
        "notes": "",
        "lines": [
            {
                "product": world.phone.pk,
                "quantity": "100",
                "unit_price": "1500.00",
                "currency": world.aud.pk,
            },
            {
                "product": world.laptop.pk,
                "quantity": "50",
                "unit_price": "2000.00",
                "currency": world.aud.pk,
            },
        ],
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def purchase_client(auth_client):
    return auth_client(User.Role.PURCHASE)


class TestPurchaseEntry:
    def test_entry_posts_pending_with_frozen_values(self, purchase_client, masterdata):
        response = purchase_client.post(PURCHASES, invoice_payload(masterdata), format="json")
        assert response.status_code == 201, response.data
        body = response.data
        assert body["status"] == PurchaseStatus.PENDING

        # Frozen AED/GST values: 100 × 1500 AUD × 2.4 = 360000 AED, GST 10%.
        phone_line = body["lines"][0]
        assert phone_line["exchange_rate"] == "2.400000"
        assert phone_line["unit_price_aed"] == "3600.00"
        assert phone_line["total_value_aed"] == "360000.00"
        assert phone_line["gst_rate_percent"] == "10.00"
        assert phone_line["gst_amount"] == "15000.00"  # AUD
        assert phone_line["gst_amount_aed"] == "36000.00"

        # Mapping row: purchase line entered → +PENDING @ purchase location.
        entries = StockLedgerEntry.objects.filter(txn_type=TxnType.PURCHASE_ENTRY)
        assert entries.count() == 2
        assert {e.bucket for e in entries} == {Bucket.PENDING}
        assert balance(masterdata.phone, masterdata.sydney, Bucket.PENDING) == (
            Decimal("100.00"),
            Decimal("360000.00"),
        )
        assert balance(masterdata.laptop, masterdata.sydney, Bucket.PENDING) == (
            Decimal("50.00"),
            Decimal("240000.00"),
        )
        assert AuditLog.objects.filter(module="purchases", action="CREATE").exists()
        assert reconciled()

    def test_entry_with_collected_qty_collects_immediately(self, purchase_client, masterdata):
        payload = invoice_payload(masterdata)
        payload["lines"][0]["collected_qty"] = "70"
        response = purchase_client.post(PURCHASES, payload, format="json")
        assert response.status_code == 201, response.data
        assert response.data["status"] == PurchaseStatus.PARTIALLY_RECEIVED
        assert response.data["lines"][0]["collected"] == "70.00"
        assert response.data["lines"][0]["pending"] == "30.00"

        assert balance(masterdata.phone, masterdata.sydney, Bucket.PENDING) == (
            Decimal("30.00"),
            Decimal("108000.00"),
        )
        assert balance(masterdata.phone, masterdata.sydney, Bucket.PHYSICAL) == (
            Decimal("70.00"),
            Decimal("252000.00"),
        )
        assert reconciled()

    def test_dubai_purchase_has_no_gst(self, purchase_client, masterdata):
        payload = invoice_payload(masterdata, location=masterdata.dubai.pk)
        payload["lines"] = [payload["lines"][0]]
        response = purchase_client.post(PURCHASES, payload, format="json")
        assert response.status_code == 201, response.data
        assert response.data["lines"][0]["gst_rate_percent"] == "0.00"
        assert response.data["lines"][0]["gst_amount"] == "0.00"

    def test_manual_exchange_rate_override(self, purchase_client, masterdata):
        payload = invoice_payload(masterdata)
        payload["lines"] = [dict(payload["lines"][0], exchange_rate="2.500000")]
        response = purchase_client.post(PURCHASES, payload, format="json")
        assert response.status_code == 201, response.data
        assert response.data["lines"][0]["unit_price_aed"] == "3750.00"

    def test_missing_exchange_rate_rejected(self, purchase_client, masterdata):
        from apps.masterdata.models import Currency

        pkr = Currency.objects.create(code="PKR")
        payload = invoice_payload(masterdata)
        payload["lines"] = [dict(payload["lines"][0], currency=pkr.pk)]
        response = purchase_client.post(PURCHASES, payload, format="json")
        assert response.status_code == 400
        assert "exchange rate" in str(response.data).lower()

    def test_non_purchase_location_rejected(self, purchase_client, masterdata):
        from apps.masterdata.models import Location

        warehouse = Location.objects.create(name="Transit Hub", can_purchase=False)
        response = purchase_client.post(
            PURCHASES, invoice_payload(masterdata, location=warehouse.pk), format="json"
        )
        assert response.status_code == 400


class TestPurchaseCollection:
    def _create(self, client, world):
        response = client.post(PURCHASES, invoice_payload(world), format="json")
        assert response.status_code == 201, response.data
        return response.data

    def test_partial_then_full_collection(self, purchase_client, masterdata):
        body = self._create(purchase_client, masterdata)
        purchase_id = body["id"]
        phone_line_id = body["lines"][0]["id"]

        # Mapping row: collection → −PENDING, +PHYSICAL @ collection location.
        response = purchase_client.post(
            f"{PURCHASES}{purchase_id}/collections/",
            {
                "collection_date": "2026-07-02",
                "lines": [{"purchase_line": phone_line_id, "quantity": "40"}],
            },
            format="json",
        )
        assert response.status_code == 201, response.data
        assert balance(masterdata.phone, masterdata.sydney, Bucket.PENDING) == (
            Decimal("60.00"),
            Decimal("216000.00"),
        )
        assert balance(masterdata.phone, masterdata.sydney, Bucket.PHYSICAL) == (
            Decimal("40.00"),
            Decimal("144000.00"),
        )

        purchase = Purchase.objects.get(pk=purchase_id)
        assert purchase.status == PurchaseStatus.PARTIALLY_RECEIVED

        # Collect the remainder; pending must land on exactly zero value.
        response = purchase_client.post(
            f"{PURCHASES}{purchase_id}/collections/",
            {
                "collection_date": "2026-07-03",
                "lines": [
                    {"purchase_line": phone_line_id, "quantity": "60"},
                    {"purchase_line": body["lines"][1]["id"], "quantity": "50"},
                ],
            },
            format="json",
        )
        assert response.status_code == 201, response.data
        assert balance(masterdata.phone, masterdata.sydney, Bucket.PENDING) == (
            Decimal("0.00"),
            Decimal("0.00"),
        )
        assert balance(masterdata.phone, masterdata.sydney, Bucket.PHYSICAL) == (
            Decimal("100.00"),
            Decimal("360000.00"),
        )
        assert Purchase.objects.get(pk=purchase_id).status == PurchaseStatus.FULLY_COLLECTED
        assert AuditLog.objects.filter(module="purchase_collections").count() == 2
        assert reconciled()

    def test_over_collection_rejected(self, purchase_client, masterdata):
        body = self._create(purchase_client, masterdata)
        response = purchase_client.post(
            f"{PURCHASES}{body['id']}/collections/",
            {
                "collection_date": "2026-07-02",
                "lines": [{"purchase_line": body["lines"][0]["id"], "quantity": "101"}],
            },
            format="json",
        )
        assert response.status_code == 400
        assert balance(masterdata.phone, masterdata.sydney, Bucket.PHYSICAL)[0] == 0
        assert reconciled()

    def test_collection_at_other_location(self, purchase_client, masterdata):
        """−PENDING stays at the purchase location; +PHYSICAL lands where the
        stock was actually collected (FR-042)."""
        body = self._create(purchase_client, masterdata)
        response = purchase_client.post(
            f"{PURCHASES}{body['id']}/collections/",
            {
                "collection_date": "2026-07-02",
                "location": masterdata.dubai.pk,
                "lines": [{"purchase_line": body["lines"][0]["id"], "quantity": "10"}],
            },
            format="json",
        )
        assert response.status_code == 201, response.data
        assert balance(masterdata.phone, masterdata.sydney, Bucket.PENDING)[0] == Decimal("90.00")
        assert balance(masterdata.phone, masterdata.dubai, Bucket.PHYSICAL)[0] == Decimal("10.00")
        assert reconciled()

    def test_delete_collection_restores_pending(self, purchase_client, masterdata):
        body = self._create(purchase_client, masterdata)
        response = purchase_client.post(
            f"{PURCHASES}{body['id']}/collections/",
            {
                "collection_date": "2026-07-02",
                "lines": [{"purchase_line": body["lines"][0]["id"], "quantity": "40"}],
            },
            format="json",
        )
        collection_id = response.data["id"]
        response = purchase_client.delete(
            f"{PURCHASES}{body['id']}/collections/{collection_id}/"
        )
        assert response.status_code == 204
        assert balance(masterdata.phone, masterdata.sydney, Bucket.PENDING) == (
            Decimal("100.00"),
            Decimal("360000.00"),
        )
        assert balance(masterdata.phone, masterdata.sydney, Bucket.PHYSICAL) == (
            Decimal("0.00"),
            Decimal("0.00"),
        )
        assert reconciled()

    def test_pending_lines_feed(self, purchase_client, masterdata):
        body = self._create(purchase_client, masterdata)
        purchase_client.post(
            f"{PURCHASES}{body['id']}/collections/",
            {
                "collection_date": "2026-07-02",
                "lines": [{"purchase_line": body["lines"][1]["id"], "quantity": "50"}],
            },
            format="json",
        )
        response = purchase_client.get(f"{PURCHASES}pending-lines/")
        assert response.status_code == 200
        rows = response.data["results"]
        assert len(rows) == 1  # laptop line fully collected, phone still pending
        assert rows[0]["invoice_no"] == "INV-001"
        assert rows[0]["pending"] == "100.00"


class TestPurchaseEditDelete:
    def _create(self, client, world, **overrides):
        response = client.post(PURCHASES, invoice_payload(world, **overrides), format="json")
        assert response.status_code == 201, response.data
        return response.data

    def _update_payload(self, body, lines):
        return {
            "invoice_no": body["invoice_no"],
            "purchase_date": body["purchase_date"],
            "location": body["location"],
            "supplier": body["supplier"],
            "notes": body["notes"],
            "lines": lines,
        }

    def test_edit_uncollected_line_reverses_and_reposts(self, purchase_client, masterdata):
        body = self._create(purchase_client, masterdata)
        line = dict(body["lines"][0])
        edited = {
            "id": line["id"],
            "product": line["product"],
            "quantity": "80",
            "unit_price": "1400.00",
            "currency": line["currency"],
            "exchange_rate": line["exchange_rate"],
            "gst_rate_percent": line["gst_rate_percent"],
        }
        keep = {
            "id": body["lines"][1]["id"],
            "product": body["lines"][1]["product"],
            "quantity": body["lines"][1]["quantity"],
            "unit_price": body["lines"][1]["unit_price"],
            "currency": body["lines"][1]["currency"],
            "exchange_rate": body["lines"][1]["exchange_rate"],
            "gst_rate_percent": body["lines"][1]["gst_rate_percent"],
        }
        response = purchase_client.put(
            f"{PURCHASES}{body['id']}/",
            self._update_payload(body, [edited, keep]),
            format="json",
        )
        assert response.status_code == 200, response.data

        # 80 × 1400 × 2.4 = 268800; old 360000 fully reversed.
        assert balance(masterdata.phone, masterdata.sydney, Bucket.PENDING) == (
            Decimal("80.00"),
            Decimal("268800.00"),
        )
        reversals = StockLedgerEntry.objects.filter(txn_type=TxnType.EDIT_REVERSAL)
        assert reversals.count() == 2  # one reversal out + one fresh in
        assert reconciled()

    def test_edit_pricing_after_collection_rejected(self, purchase_client, masterdata):
        body = self._create(purchase_client, masterdata)
        purchase_client.post(
            f"{PURCHASES}{body['id']}/collections/",
            {
                "collection_date": "2026-07-02",
                "lines": [{"purchase_line": body["lines"][0]["id"], "quantity": "40"}],
            },
            format="json",
        )
        line = body["lines"][0]
        edited = {
            "id": line["id"],
            "product": line["product"],
            "quantity": line["quantity"],
            "unit_price": "999.00",
            "currency": line["currency"],
            "exchange_rate": line["exchange_rate"],
            "gst_rate_percent": line["gst_rate_percent"],
        }
        keep = {
            "id": body["lines"][1]["id"],
            "product": body["lines"][1]["product"],
            "quantity": body["lines"][1]["quantity"],
            "unit_price": body["lines"][1]["unit_price"],
            "currency": body["lines"][1]["currency"],
            "exchange_rate": body["lines"][1]["exchange_rate"],
            "gst_rate_percent": body["lines"][1]["gst_rate_percent"],
        }
        response = purchase_client.put(
            f"{PURCHASES}{body['id']}/",
            self._update_payload(body, [edited, keep]),
            format="json",
        )
        assert response.status_code == 400
        assert reconciled()

    def test_quantity_below_collected_rejected(self, purchase_client, masterdata):
        body = self._create(purchase_client, masterdata)
        purchase_client.post(
            f"{PURCHASES}{body['id']}/collections/",
            {
                "collection_date": "2026-07-02",
                "lines": [{"purchase_line": body["lines"][0]["id"], "quantity": "40"}],
            },
            format="json",
        )
        line = body["lines"][0]
        edited = {
            "id": line["id"],
            "product": line["product"],
            "quantity": "30",  # below the 40 already collected
            "unit_price": line["unit_price"],
            "currency": line["currency"],
            "exchange_rate": line["exchange_rate"],
            "gst_rate_percent": line["gst_rate_percent"],
        }
        keep = {
            "id": body["lines"][1]["id"],
            "product": body["lines"][1]["product"],
            "quantity": body["lines"][1]["quantity"],
            "unit_price": body["lines"][1]["unit_price"],
            "currency": body["lines"][1]["currency"],
            "exchange_rate": body["lines"][1]["exchange_rate"],
            "gst_rate_percent": body["lines"][1]["gst_rate_percent"],
        }
        response = purchase_client.put(
            f"{PURCHASES}{body['id']}/",
            self._update_payload(body, [edited, keep]),
            format="json",
        )
        assert response.status_code == 400
        assert reconciled()

    def test_soft_delete_purchase_reverses_everything(self, purchase_client, masterdata):
        body = self._create(purchase_client, masterdata)
        purchase_client.post(
            f"{PURCHASES}{body['id']}/collections/",
            {
                "collection_date": "2026-07-02",
                "lines": [{"purchase_line": body["lines"][0]["id"], "quantity": "40"}],
            },
            format="json",
        )
        response = purchase_client.delete(f"{PURCHASES}{body['id']}/")
        assert response.status_code == 204

        # §5.2 soft delete → reversal rows only; record survives, flagged.
        purchase = Purchase.objects.get(pk=body["id"])
        assert purchase.is_deleted
        for product in (masterdata.phone, masterdata.laptop):
            assert balance(product, masterdata.sydney, Bucket.PENDING) == (
                Decimal("0.00"),
                Decimal("0.00"),
            )
            assert balance(product, masterdata.sydney, Bucket.PHYSICAL) == (
                Decimal("0.00"),
                Decimal("0.00"),
            )
        assert StockLedgerEntry.objects.filter(txn_type=TxnType.DELETE_REVERSAL).exists()
        assert AuditLog.objects.filter(
            module="purchases", action="DELETE", record_id=body["id"]
        ).exists()
        # Deleted purchases disappear from the list but history stays in the ledger.
        response = purchase_client.get(PURCHASES)
        assert response.data["count"] == 0
        assert reconciled()

    def test_list_quick_totals(self, purchase_client, masterdata):
        self._create(purchase_client, masterdata)
        response = purchase_client.get(PURCHASES)
        totals = response.data["totals"]
        assert totals["total_quantity"] == "150.00"
        assert totals["total_value_aed"] == "600000.00"
        assert totals["total_gst_aed"] == "60000.00"


class TestPurchasePermissions:
    @pytest.mark.parametrize(
        "role,expected",
        [
            (User.Role.ADMIN, 201),
            (User.Role.PURCHASE, 201),
            (User.Role.SALE, 403),
            (User.Role.VIEWER, 403),
        ],
    )
    def test_create_by_role(self, auth_client, masterdata, role, expected):
        client = auth_client(role)
        response = client.post(PURCHASES, invoice_payload(masterdata), format="json")
        assert response.status_code == expected

    def test_all_roles_can_read(self, auth_client, purchase_client, masterdata):
        purchase_client.post(PURCHASES, invoice_payload(masterdata), format="json")
        for role in (User.Role.SALE, User.Role.VIEWER):
            client = auth_client(role)
            assert client.get(PURCHASES).status_code == 200

    def test_sale_user_cannot_collect(self, auth_client, purchase_client, masterdata):
        body = purchase_client.post(PURCHASES, invoice_payload(masterdata), format="json").data
        client = auth_client(User.Role.SALE)
        response = client.post(
            f"{PURCHASES}{body['id']}/collections/",
            {
                "collection_date": "2026-07-02",
                "lines": [{"purchase_line": body["lines"][0]["id"], "quantity": "1"}],
            },
            format="json",
        )
        assert response.status_code == 403
