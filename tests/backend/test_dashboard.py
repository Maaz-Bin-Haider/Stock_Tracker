"""Dashboard endpoint tests (FR-094…FR-096, FR-128): live cards read the
materialized balances, past snapshots aggregate the ledger at the cutoff, and
"today" boundaries are Dubai business time."""

from decimal import Decimal

import pytest

from apps.accounts.models import User
from apps.inventory.services import rebuild_stock_balances

pytestmark = pytest.mark.django_db

DASHBOARD = "/api/v1/reports/dashboard/"


def location_row(data, name):
    return next(row for row in data["stock_by_location"] if row["location"] == name)


class TestLiveDashboard:
    def test_cards_match_ledger_state(self, report_world):
        response = report_world.admin_client.get(DASHBOARD)
        assert response.status_code == 200
        cards = response.data["cards"]

        # Sydney phone 2 + Dubai phone 2 + Dubai laptop 18 = 22 physical.
        assert cards["total_physical"] == Decimal("22.00")
        assert cards["total_pending"] == Decimal("2.00")
        assert cards["total_in_transit"] == Decimal("1.00")
        # GST: 240 AED at entry − 48 (pending cancel) − 24 (received refund).
        assert cards["gst_total_aed"] == Decimal("168.00")
        assert cards["todays_sales"]["quantity"] == Decimal("2.00")
        assert cards["todays_sales"]["lines"] == 1
        assert response.data["as_of"] is None
        assert rebuild_stock_balances() == []

    def test_sales_location_cards(self, report_world):
        response = report_world.admin_client.get(DASHBOARD)
        dubai = next(
            card
            for card in response.data["cards"]["sales_locations"]
            if card["location"] == "Dubai"
        )
        assert dubai["physical"] == Decimal("20.00")  # 2 phone + 18 laptop
        assert dubai["in_transit"] == Decimal("1.00")

    def test_stock_by_location(self, report_world):
        response = report_world.admin_client.get(DASHBOARD)
        sydney = location_row(response.data, "Sydney")
        assert sydney["physical"] == Decimal("2.00")
        assert sydney["pending"] == Decimal("2.00")
        assert sydney["in_transit"] == Decimal("0.00")

    def test_viewer_can_see_dashboard(self, report_world, auth_client):
        response = auth_client(User.Role.VIEWER).get(DASHBOARD)
        assert response.status_code == 200

    def test_anonymous_rejected(self, report_world, client):
        assert client.get(DASHBOARD).status_code in (401, 403)


class TestPastSnapshot:
    def test_cutoff_excludes_later_events(self, report_world):
        """At mid_cutoff the shipment/sales/adjustment had not happened yet."""
        cutoff = report_world.mid_cutoff.isoformat()
        response = report_world.admin_client.get(DASHBOARD, {"cutoff": cutoff})
        assert response.status_code == 200
        cards = response.data["cards"]

        # Sydney phone 5 + Dubai laptop 20 = 25 physical; nothing in transit.
        assert cards["total_physical"] == Decimal("25.00")
        assert cards["total_pending"] == Decimal("2.00")
        assert cards["total_in_transit"] == Decimal("0.00")
        # Refunds already existed at the cutoff, so GST is already net.
        assert cards["gst_total_aed"] == Decimal("168.00")
        assert response.data["as_of"] is not None

        sydney = location_row(response.data, "Sydney")
        assert sydney["physical"] == Decimal("5.00")

    def test_ancient_cutoff_is_empty(self, report_world):
        response = report_world.admin_client.get(
            DASHBOARD, {"cutoff": "2020-01-01T00:00:00+00:00"}
        )
        cards = response.data["cards"]
        assert cards["total_physical"] == Decimal("0.00")
        assert cards["gst_total_aed"] == Decimal("0.00")

    def test_invalid_cutoff_rejected(self, report_world):
        response = report_world.admin_client.get(DASHBOARD, {"cutoff": "not-a-date"})
        assert response.status_code == 400
