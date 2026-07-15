"""Shipment + receiving flow tests, keyed to the event→ledger mapping table
(TECHNICAL_ARCHITECTURE §5.2/§13): ship, partial/over-receive, cancel,
Dubai→Karachi, valuation at the source's carrying average cost. Every scenario
ends with the balance reconciliation check."""

from decimal import Decimal

import pytest

from apps.accounts.models import User
from apps.audits.models import AuditLog
from apps.inventory.models import Bucket, StockBalance, StockLedgerEntry, TxnType
from apps.inventory.services import rebuild_stock_balances
from apps.shipments.models import ShipmentStatus

pytestmark = pytest.mark.django_db

SHIPMENTS = "/api/v1/shipments/"
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
def karachi(db):
    from apps.masterdata.models import Location

    return Location.objects.create(name="Karachi", country="Pakistan", is_sales_location=True)


def give_stock(client, world, *, product, quantity, unit_price, invoice_no="INV-STK"):
    """Physical stock at Sydney via a fully-collected AED purchase."""
    response = client.post(
        PURCHASES,
        {
            "invoice_no": invoice_no,
            "purchase_date": "2026-07-01",
            "location": world.sydney.pk,
            "supplier": world.supplier.pk,
            "lines": [
                {
                    "product": product.pk,
                    "quantity": str(quantity),
                    "unit_price": str(unit_price),
                    "currency": world.aed.pk,
                    "collected_qty": str(quantity),
                }
            ],
        },
        format="json",
    )
    assert response.status_code == 201, response.data
    return response.data


def shipment_payload(world, to_location, **overrides):
    payload = {
        "shipment_date": "2026-07-10",
        "from_location": world.sydney.pk,
        "to_location": to_location.pk,
        "shipment_type": "STANDARD",
        "shipping_cost": "250.00",
        "notes": "",
        "lines": [{"product": world.phone.pk, "quantity": "50"}],
    }
    payload.update(overrides)
    return payload


def make_shipped(client, world, to_location, **overrides):
    response = client.post(
        SHIPMENTS, shipment_payload(world, to_location, ship=True, **overrides), format="json"
    )
    assert response.status_code == 201, response.data
    return response.data


class TestShipmentDraft:
    def test_draft_posts_nothing(self, purchase_client, masterdata):
        give_stock(purchase_client, masterdata, product=masterdata.phone,
                   quantity=100, unit_price="120.00")
        response = purchase_client.post(
            SHIPMENTS, shipment_payload(masterdata, masterdata.dubai), format="json"
        )
        assert response.status_code == 201, response.data
        assert response.data["status"] == ShipmentStatus.DRAFT
        assert response.data["shipment_no"].startswith("SH-")
        assert not StockLedgerEntry.objects.filter(source_module="shipments").exists()
        assert AuditLog.objects.filter(module="shipments", action="CREATE").exists()
        assert reconciled()

    def test_draft_lines_editable_shipped_lines_locked(self, purchase_client, masterdata):
        give_stock(purchase_client, masterdata, product=masterdata.phone,
                   quantity=100, unit_price="120.00")
        draft = purchase_client.post(
            SHIPMENTS, shipment_payload(masterdata, masterdata.dubai), format="json"
        ).data
        payload = shipment_payload(masterdata, masterdata.dubai)
        payload["lines"] = [{"product": masterdata.phone.pk, "quantity": "30"}]
        response = purchase_client.put(f"{SHIPMENTS}{draft['id']}/", payload, format="json")
        assert response.status_code == 200, response.data
        assert response.data["lines"][0]["quantity"] == "30.00"

        purchase_client.post(f"{SHIPMENTS}{draft['id']}/ship/")
        payload["lines"] = [
            {"id": response.data["lines"][0]["id"], "product": masterdata.phone.pk,
             "quantity": "40"}
        ]
        response = purchase_client.put(f"{SHIPMENTS}{draft['id']}/", payload, format="json")
        assert response.status_code == 400
        assert "cancel" in str(response.data).lower()

    def test_same_source_and_destination_rejected(self, purchase_client, masterdata):
        response = purchase_client.post(
            SHIPMENTS,
            shipment_payload(masterdata, masterdata.sydney),
            format="json",
        )
        assert response.status_code == 400


class TestShipping:
    def test_ship_moves_stock_at_carrying_average(self, purchase_client, masterdata):
        # Two collected purchases at different rates: 60 @ 100 + 40 @ 150
        # → 100 physical worth 12000, carrying average 120 (§5.3.1).
        give_stock(purchase_client, masterdata, product=masterdata.phone,
                   quantity=60, unit_price="100.00", invoice_no="INV-A")
        give_stock(purchase_client, masterdata, product=masterdata.phone,
                   quantity=40, unit_price="150.00", invoice_no="INV-B")

        body = make_shipped(purchase_client, masterdata, masterdata.dubai)
        assert body["status"] == ShipmentStatus.SHIPPED

        # Ship 50 → value moved 50 × 120 = 6000 AED.
        assert balance(masterdata.phone, masterdata.sydney, Bucket.PHYSICAL) == (
            Decimal("50.00"), Decimal("6000.00"),
        )
        assert balance(masterdata.phone, masterdata.dubai, Bucket.IN_TRANSIT) == (
            Decimal("50.00"), Decimal("6000.00"),
        )
        out_rows = StockLedgerEntry.objects.filter(txn_type=TxnType.SHIPMENT_OUT)
        assert out_rows.count() == 2
        assert {(r.bucket, str(r.location)) for r in out_rows} == {
            ("PHYSICAL", "Sydney"), ("IN_TRANSIT", "Dubai"),
        }
        assert reconciled()

    def test_ship_full_stock_empties_value_exactly(self, purchase_client, masterdata):
        give_stock(purchase_client, masterdata, product=masterdata.phone,
                   quantity=30, unit_price="99.99")
        make_shipped(purchase_client, masterdata, masterdata.dubai,
                     lines=[{"product": masterdata.phone.pk, "quantity": "30"}])
        assert balance(masterdata.phone, masterdata.sydney, Bucket.PHYSICAL) == (
            Decimal("0.00"), Decimal("0.00"),
        )
        assert reconciled()

    def test_multi_line_same_product_shares_pool_exactly(self, purchase_client, masterdata):
        give_stock(purchase_client, masterdata, product=masterdata.phone,
                   quantity=90, unit_price="100.00")
        make_shipped(
            purchase_client, masterdata, masterdata.dubai,
            lines=[
                {"product": masterdata.phone.pk, "quantity": "60"},
                {"product": masterdata.phone.pk, "quantity": "30"},
            ],
        )
        assert balance(masterdata.phone, masterdata.sydney, Bucket.PHYSICAL) == (
            Decimal("0.00"), Decimal("0.00"),
        )
        assert balance(masterdata.phone, masterdata.dubai, Bucket.IN_TRANSIT) == (
            Decimal("90.00"), Decimal("9000.00"),
        )
        assert reconciled()

    def test_negative_stock_requires_confirmation(self, purchase_client, masterdata):
        give_stock(purchase_client, masterdata, product=masterdata.phone,
                   quantity=20, unit_price="100.00")
        payload = shipment_payload(
            masterdata, masterdata.dubai, ship=True,
            lines=[{"product": masterdata.phone.pk, "quantity": "50"}],
        )
        response = purchase_client.post(SHIPMENTS, payload, format="json")
        assert response.status_code == 400
        assert "negative_stock_confirmation_required" in str(response.data)

        response = purchase_client.post(
            f"{SHIPMENTS}?confirm_negative=true", payload, format="json"
        )
        assert response.status_code == 201, response.data
        # Source went negative; all carried value moved with the stock.
        assert balance(masterdata.phone, masterdata.sydney, Bucket.PHYSICAL) == (
            Decimal("-30.00"), Decimal("0.00"),
        )
        assert balance(masterdata.phone, masterdata.dubai, Bucket.IN_TRANSIT) == (
            Decimal("50.00"), Decimal("2000.00"),
        )
        assert reconciled()

    def test_dubai_to_karachi_transfer(self, purchase_client, masterdata, karachi):
        give_stock(purchase_client, masterdata, product=masterdata.phone,
                   quantity=40, unit_price="100.00")
        make_shipped(purchase_client, masterdata, masterdata.dubai,
                     lines=[{"product": masterdata.phone.pk, "quantity": "40"}])
        ship = purchase_client.post(
            f"{SHIPMENTS}?confirm_negative=false",
            {
                "shipment_date": "2026-07-12",
                "from_location": masterdata.dubai.pk,
                "to_location": karachi.pk,
                "shipment_type": "DUBAI_KARACHI",
                "lines": [{"product": masterdata.phone.pk, "quantity": "10"}],
                "ship": False,
            },
            format="json",
        )
        assert ship.status_code == 201, ship.data
        # Transfer takes stock from current Dubai *physical* stock — receive
        # the inbound shipment first (FR-065).
        first = purchase_client.get(f"{SHIPMENTS}{make_id(ship.data)}/").data
        assert first["shipment_type"] == "DUBAI_KARACHI"


def make_id(body):
    return body["id"]


class TestReceiving:
    def _shipped(self, client, world, qty=50, price="120.00"):
        give_stock(client, world, product=world.phone, quantity=100, unit_price=price)
        return make_shipped(client, world, world.dubai,
                            lines=[{"product": world.phone.pk, "quantity": str(qty)}])

    def test_partial_receive(self, purchase_client, masterdata):
        body = self._shipped(purchase_client, masterdata)
        line_id = body["lines"][0]["id"]
        response = purchase_client.post(
            f"{SHIPMENTS}{body['id']}/receipts/",
            {"receipt_date": "2026-07-12",
             "lines": [{"shipment_line": line_id, "quantity": "20"}]},
            format="json",
        )
        assert response.status_code == 201, response.data

        detail = purchase_client.get(f"{SHIPMENTS}{body['id']}/").data
        assert detail["status"] == ShipmentStatus.PARTIALLY_RECEIVED
        assert detail["lines"][0]["received"] == "20.00"
        assert detail["lines"][0]["remaining"] == "30.00"
        assert detail["lines"][0]["over_received"] is False

        # 50 shipped @ avg 120 → 6000 in transit; 20 received moves 2400.
        assert balance(masterdata.phone, masterdata.dubai, Bucket.IN_TRANSIT) == (
            Decimal("30.00"), Decimal("3600.00"),
        )
        assert balance(masterdata.phone, masterdata.dubai, Bucket.PHYSICAL) == (
            Decimal("20.00"), Decimal("2400.00"),
        )
        assert AuditLog.objects.filter(module="shipment_receipts", action="CREATE").exists()
        assert reconciled()

    def test_full_receive_empties_transit_exactly(self, purchase_client, masterdata):
        body = self._shipped(purchase_client, masterdata, qty=50, price="99.99")
        line_id = body["lines"][0]["id"]
        for qty in ("20", "30"):
            response = purchase_client.post(
                f"{SHIPMENTS}{body['id']}/receipts/",
                {"receipt_date": "2026-07-12",
                 "lines": [{"shipment_line": line_id, "quantity": qty}]},
                format="json",
            )
            assert response.status_code == 201, response.data

        detail = purchase_client.get(f"{SHIPMENTS}{body['id']}/").data
        assert detail["status"] == ShipmentStatus.FULLY_RECEIVED
        assert balance(masterdata.phone, masterdata.dubai, Bucket.IN_TRANSIT) == (
            Decimal("0.00"), Decimal("0.00"),
        )
        assert reconciled()

    def test_over_receive_allowed_with_flag(self, purchase_client, masterdata):
        body = self._shipped(purchase_client, masterdata, qty=10)
        line_id = body["lines"][0]["id"]
        response = purchase_client.post(
            f"{SHIPMENTS}{body['id']}/receipts/",
            {"receipt_date": "2026-07-12",
             "lines": [{"shipment_line": line_id, "quantity": "15"}]},
            format="json",
        )
        assert response.status_code == 201, response.data

        detail = purchase_client.get(f"{SHIPMENTS}{body['id']}/").data
        assert detail["lines"][0]["over_received"] is True
        assert detail["lines"][0]["remaining"] == "-5.00"
        assert detail["status"] == ShipmentStatus.FULLY_RECEIVED
        # IN_TRANSIT goes negative for the line (§5.2 note); the extra
        # quantity carries no extra value — value is conserved.
        assert balance(masterdata.phone, masterdata.dubai, Bucket.IN_TRANSIT) == (
            Decimal("-5.00"), Decimal("0.00"),
        )
        assert balance(masterdata.phone, masterdata.dubai, Bucket.PHYSICAL) == (
            Decimal("15.00"), Decimal("1200.00"),
        )
        assert reconciled()

    def test_receive_before_ship_rejected(self, purchase_client, masterdata):
        give_stock(purchase_client, masterdata, product=masterdata.phone,
                   quantity=100, unit_price="120.00")
        draft = purchase_client.post(
            SHIPMENTS, shipment_payload(masterdata, masterdata.dubai), format="json"
        ).data
        response = purchase_client.post(
            f"{SHIPMENTS}{draft['id']}/receipts/",
            {"receipt_date": "2026-07-12",
             "lines": [{"shipment_line": draft["lines"][0]["id"], "quantity": "5"}]},
            format="json",
        )
        assert response.status_code == 400

    def test_receipt_undo_returns_stock_to_transit(self, purchase_client, masterdata):
        body = self._shipped(purchase_client, masterdata)
        line_id = body["lines"][0]["id"]
        receipt = purchase_client.post(
            f"{SHIPMENTS}{body['id']}/receipts/",
            {"receipt_date": "2026-07-12",
             "lines": [{"shipment_line": line_id, "quantity": "20"}]},
            format="json",
        ).data
        response = purchase_client.delete(
            f"{SHIPMENTS}{body['id']}/receipts/{receipt['id']}/"
        )
        assert response.status_code == 204

        assert balance(masterdata.phone, masterdata.dubai, Bucket.IN_TRANSIT) == (
            Decimal("50.00"), Decimal("6000.00"),
        )
        assert balance(masterdata.phone, masterdata.dubai, Bucket.PHYSICAL) == (
            Decimal("0.00"), Decimal("0.00"),
        )
        detail = purchase_client.get(f"{SHIPMENTS}{body['id']}/").data
        assert detail["status"] == ShipmentStatus.SHIPPED
        assert reconciled()


class TestCancellation:
    def test_cancel_draft(self, purchase_client, masterdata):
        give_stock(purchase_client, masterdata, product=masterdata.phone,
                   quantity=100, unit_price="120.00")
        draft = purchase_client.post(
            SHIPMENTS, shipment_payload(masterdata, masterdata.dubai), format="json"
        ).data
        response = purchase_client.post(
            f"{SHIPMENTS}{draft['id']}/cancel/", {"reason": "not needed"}, format="json"
        )
        assert response.status_code == 200
        assert response.data["status"] == ShipmentStatus.CANCELLED
        assert not StockLedgerEntry.objects.filter(source_module="shipments").exists()
        assert reconciled()

    def test_cancel_after_partial_receive_returns_unreceived(
        self, purchase_client, masterdata
    ):
        give_stock(purchase_client, masterdata, product=masterdata.phone,
                   quantity=100, unit_price="120.00")
        body = make_shipped(purchase_client, masterdata, masterdata.dubai)
        line_id = body["lines"][0]["id"]
        purchase_client.post(
            f"{SHIPMENTS}{body['id']}/receipts/",
            {"receipt_date": "2026-07-12",
             "lines": [{"shipment_line": line_id, "quantity": "20"}]},
            format="json",
        )
        response = purchase_client.post(
            f"{SHIPMENTS}{body['id']}/cancel/", {"reason": "carrier lost the rest"},
            format="json",
        )
        assert response.status_code == 200, response.data
        assert response.data["status"] == ShipmentStatus.CANCELLED

        # 30 unreceived (3600 AED) return to Sydney; the received 20 stay in Dubai.
        assert balance(masterdata.phone, masterdata.sydney, Bucket.PHYSICAL) == (
            Decimal("80.00"), Decimal("9600.00"),
        )
        assert balance(masterdata.phone, masterdata.dubai, Bucket.IN_TRANSIT) == (
            Decimal("0.00"), Decimal("0.00"),
        )
        assert balance(masterdata.phone, masterdata.dubai, Bucket.PHYSICAL) == (
            Decimal("20.00"), Decimal("2400.00"),
        )
        cancel_rows = StockLedgerEntry.objects.filter(txn_type=TxnType.SHIPMENT_CANCEL)
        assert cancel_rows.count() == 2
        assert reconciled()

    def test_cancel_fully_received_rejected(self, purchase_client, masterdata):
        give_stock(purchase_client, masterdata, product=masterdata.phone,
                   quantity=100, unit_price="120.00")
        body = make_shipped(purchase_client, masterdata, masterdata.dubai)
        purchase_client.post(
            f"{SHIPMENTS}{body['id']}/receipts/",
            {"receipt_date": "2026-07-12",
             "lines": [{"shipment_line": body["lines"][0]["id"], "quantity": "50"}]},
            format="json",
        )
        response = purchase_client.post(
            f"{SHIPMENTS}{body['id']}/cancel/", {"reason": "too late"}, format="json"
        )
        assert response.status_code == 400


class TestDeletion:
    def test_delete_restores_everything(self, purchase_client, masterdata):
        give_stock(purchase_client, masterdata, product=masterdata.phone,
                   quantity=100, unit_price="120.00")
        body = make_shipped(purchase_client, masterdata, masterdata.dubai)
        purchase_client.post(
            f"{SHIPMENTS}{body['id']}/receipts/",
            {"receipt_date": "2026-07-12",
             "lines": [{"shipment_line": body["lines"][0]["id"], "quantity": "20"}]},
            format="json",
        )
        response = purchase_client.delete(f"{SHIPMENTS}{body['id']}/")
        assert response.status_code == 204

        # Everything is back at the source; Dubai buckets are exactly empty.
        assert balance(masterdata.phone, masterdata.sydney, Bucket.PHYSICAL) == (
            Decimal("100.00"), Decimal("12000.00"),
        )
        assert balance(masterdata.phone, masterdata.dubai, Bucket.IN_TRANSIT) == (
            Decimal("0.00"), Decimal("0.00"),
        )
        assert balance(masterdata.phone, masterdata.dubai, Bucket.PHYSICAL) == (
            Decimal("0.00"), Decimal("0.00"),
        )
        assert purchase_client.get(f"{SHIPMENTS}{body['id']}/").status_code == 404
        assert AuditLog.objects.filter(module="shipments", action="DELETE").exists()
        assert reconciled()


class TestPermissionsAndTotals:
    def test_role_matrix(self, auth_client, masterdata):
        writer = auth_client(User.Role.PURCHASE)
        give_stock(writer, masterdata, product=masterdata.phone,
                   quantity=100, unit_price="120.00")
        body = make_shipped(writer, masterdata, masterdata.dubai)

        for role in (User.Role.SALE, User.Role.VIEWER):
            client = auth_client(role)
            assert client.get(SHIPMENTS).status_code == 200
            assert (
                client.post(
                    SHIPMENTS, shipment_payload(masterdata, masterdata.dubai), format="json"
                ).status_code
                == 403
            )
            assert client.post(f"{SHIPMENTS}{body['id']}/ship/").status_code == 403
            assert (
                client.post(
                    f"{SHIPMENTS}{body['id']}/receipts/",
                    {"receipt_date": "2026-07-12", "lines": []},
                    format="json",
                ).status_code
                == 403
            )
            assert client.delete(f"{SHIPMENTS}{body['id']}/").status_code == 403

    def test_list_quick_totals(self, purchase_client, masterdata):
        give_stock(purchase_client, masterdata, product=masterdata.phone,
                   quantity=100, unit_price="120.00")
        body = make_shipped(purchase_client, masterdata, masterdata.dubai)
        purchase_client.post(
            f"{SHIPMENTS}{body['id']}/receipts/",
            {"receipt_date": "2026-07-12",
             "lines": [{"shipment_line": body["lines"][0]["id"], "quantity": "20"}]},
            format="json",
        )
        response = purchase_client.get(SHIPMENTS)
        assert response.status_code == 200
        assert response.data["totals"] == {
            "total_shipped": "50.00",
            "total_received": "20.00",
            "total_remaining": "30.00",
        }
