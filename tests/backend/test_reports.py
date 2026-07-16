"""Report endpoint tests (SRS §5): every report is filterable, GST nets out
refunds from frozen line values, valuation is admin-only and reconciles with
the ledger-derived balances."""

from decimal import Decimal

import pytest

from apps.accounts.models import User
from apps.inventory.services import rebuild_stock_balances

pytestmark = pytest.mark.django_db

REPORTS = "/api/v1/reports/"


def rows(response, section=0):
    return response.data["sections"][section]["rows"]


def only_row(response, **match):
    matches = [
        row
        for row in rows(response)
        if all(row.get(key) == value for key, value in match.items())
    ]
    assert len(matches) == 1, f"expected one row matching {match}, got {matches}"
    return matches[0]


class TestReportIndex:
    def test_admin_sees_valuation_reports(self, report_world):
        response = report_world.admin_client.get(REPORTS)
        keys = {report["key"] for report in response.data}
        assert "stock-valuation-summary" in keys
        assert "stock-valuation-detail" in keys
        assert "gst-report" in keys

    def test_non_admin_does_not_see_valuation(self, report_world, auth_client):
        response = auth_client(User.Role.VIEWER).get(REPORTS)
        keys = {report["key"] for report in response.data}
        assert "stock-valuation-summary" not in keys
        assert "purchase-report" in keys

    def test_unknown_report_404(self, report_world):
        assert report_world.admin_client.get(f"{REPORTS}nope/").status_code == 404


class TestStockReports:
    def test_current_stock_by_location(self, report_world):
        response = report_world.admin_client.get(f"{REPORTS}current-stock-by-location/")
        sydney_phone = only_row(response, location="Sydney", product="iPhone 15 Pro")
        assert sydney_phone["physical_qty"] == Decimal("2.00")
        assert sydney_phone["pending_qty"] == Decimal("2.00")
        assert sydney_phone["negative"] is False
        dubai_phone = only_row(response, location="Dubai", product="iPhone 15 Pro")
        assert dubai_phone["physical_qty"] == Decimal("2.00")
        assert dubai_phone["in_transit_qty"] == Decimal("1.00")
        assert rebuild_stock_balances() == []

    def test_current_stock_location_filter(self, report_world):
        response = report_world.admin_client.get(
            f"{REPORTS}current-stock-by-location/", {"location": report_world.sydney.pk}
        )
        assert {row["location"] for row in rows(response)} == {"Sydney"}

    def test_total_company_stock_admin_sees_value(self, report_world):
        response = report_world.admin_client.get(f"{REPORTS}total-company-stock/")
        phone = only_row(response, product="iPhone 15 Pro")
        assert phone["physical_qty"] == Decimal("4.00")
        assert phone["pending_qty"] == Decimal("2.00")
        assert phone["in_transit_qty"] == Decimal("1.00")
        assert phone["total_qty"] == Decimal("7.00")
        # 480 Sydney physical + 480 pending + 240 in transit + 480 Dubai.
        assert phone["value_aed"] == Decimal("1680.00")

    def test_total_company_stock_value_stripped_for_non_admin(self, report_world, auth_client):
        response = auth_client(User.Role.PURCHASE).get(f"{REPORTS}total-company-stock/")
        assert response.status_code == 200
        columns = {column["key"] for column in response.data["sections"][0]["columns"]}
        assert "value_aed" not in columns
        assert all("value_aed" not in row for row in rows(response))

    def test_australia_combined_stock(self, report_world):
        response = report_world.admin_client.get(f"{REPORTS}australia-combined-stock/")
        phone = only_row(response, product="iPhone 15 Pro")
        assert phone[f"loc_{report_world.sydney.pk}"] == Decimal("2.00")
        assert phone["total_au_qty"] == Decimal("2.00")
        assert phone["pending_au_qty"] == Decimal("2.00")
        assert phone["in_transit_from_au_qty"] == Decimal("1.00")

    def test_dubai_stock_report(self, report_world):
        response = report_world.admin_client.get(f"{REPORTS}dubai-stock/")
        laptop = only_row(response, product="MacBook Air")
        assert laptop["available_qty"] == Decimal("18.00")
        assert laptop["sold_today_qty"] == Decimal("2.00")
        phone = only_row(response, product="iPhone 15 Pro")
        assert phone["in_transit_qty"] == Decimal("1.00")


class TestPurchaseSideReports:
    def test_pending_purchase_stock(self, report_world):
        response = report_world.admin_client.get(f"{REPORTS}pending-purchase-stock/")
        row = only_row(response, invoice_no="INV-P1")
        assert row["pending_qty"] == Decimal("2.00")
        assert row["cancelled_qty"] == Decimal("2.00")
        assert row["aed_value_pending"] == Decimal("480.00")
        assert row["gst_pending"] == Decimal("48.00")

    def test_pending_purchase_by_location(self, report_world):
        response = report_world.admin_client.get(
            f"{REPORTS}pending-purchase-stock-by-location/"
        )
        row = only_row(response, location="Sydney")
        assert row["pending_qty"] == Decimal("2.00")
        assert row["suppliers"] == "Apple Distributor Sydney"
        assert str(row["oldest_pending_date"]) == "2026-07-01"

    def test_in_transit_stock(self, report_world):
        response = report_world.admin_client.get(f"{REPORTS}in-transit-stock/")
        row = only_row(response, from_location="Sydney")
        assert row["shipped_qty"] == Decimal("3.00")
        assert row["received_qty"] == Decimal("2.00")
        assert row["remaining_qty"] == Decimal("1.00")
        assert row["over_received_qty"] == Decimal("0.00")
        assert row["status"] == "PARTIALLY_RECEIVED"

    def test_purchase_report_and_filters(self, report_world):
        response = report_world.admin_client.get(f"{REPORTS}purchase-report/")
        assert {row["invoice_no"] for row in rows(response)} == {"INV-P1", "INV-P2"}
        row = only_row(response, invoice_no="INV-P1")
        assert row["quantity"] == Decimal("10.00")
        assert row["collected_qty"] == Decimal("6.00")
        assert row["refunded_qty"] == Decimal("3.00")
        assert row["unit_price_aed"] == Decimal("240.00")

        filtered = report_world.admin_client.get(
            f"{REPORTS}purchase-report/", {"location": report_world.sydney.pk}
        )
        assert {row["invoice_no"] for row in rows(filtered)} == {"INV-P1"}

        dated = report_world.admin_client.get(
            f"{REPORTS}purchase-report/", {"date_from": "2026-07-02"}
        )
        assert {row["invoice_no"] for row in rows(dated)} == {"INV-P2"}

    def test_gst_report_nets_out_refunds(self, report_world):
        response = report_world.admin_client.get(f"{REPORTS}gst-report/")
        row = only_row(response, invoice_no="INV-P1")
        assert row["net_qty"] == Decimal("7.00")
        assert row["gst_rate_percent"] == Decimal("10.00")
        assert row["gst_amount"] == Decimal("100.00")  # AUD, frozen at entry
        assert row["gst_reversal"] == Decimal("30.00")  # 2 + 1 units @ 10 AUD
        assert row["net_gst"] == Decimal("70.00")
        assert "RF-" in row["refund_reference"]
        # Dubai purchase has no GST region and no GST → not in the report.
        assert {r["invoice_no"] for r in rows(response)} == {"INV-P1"}
        assert response.data["totals"]["Net GST (AED)"] == Decimal("168.00")

    def test_refund_cancellation_report(self, report_world):
        response = report_world.admin_client.get(f"{REPORTS}refund-cancellation-report/")
        assert len(rows(response)) == 2
        pending = only_row(response, pending_qty_affected=Decimal("2.00"))
        assert pending["value_reversal_aed"] == Decimal("480.00")
        assert pending["gst_reversal_aed"] == Decimal("48.00")
        received = only_row(response, received_qty_affected=Decimal("1.00"))
        assert received["value_reversal_aed"] == Decimal("240.00")
        assert response.data["totals"]["AED reversed"] == Decimal("720.00")


class TestSalesAndActivityReports:
    def test_sales_report(self, report_world):
        response = report_world.admin_client.get(f"{REPORTS}sales-report/")
        assert len(rows(response)) == 2
        assert response.data["totals"]["Quantity"] == Decimal("3.00")
        priced = only_row(response, quantity=Decimal("2.00"))
        assert priced["unit_price"] == Decimal("80.00")

        filtered = report_world.admin_client.get(
            f"{REPORTS}sales-report/", {"date_from": str(report_world.today)}
        )
        assert len(rows(filtered)) == 1

    def test_party_wise_sales_grouped_by_customer(self, report_world):
        response = report_world.admin_client.get(f"{REPORTS}party-wise-sales/")
        assert response.data["sections"][0]["columns"][0]["key"] == "customer"
        assert all(row["customer"] == "Report Customer" for row in rows(response))

    def test_stock_ledger_report(self, report_world):
        response = report_world.admin_client.get(f"{REPORTS}stock-ledger/")
        assert response.data["totals"]["Rows"] > 0
        assert response.data["totals"]["Qty in"] > response.data["totals"]["Qty out"]

        filtered = report_world.admin_client.get(
            f"{REPORTS}stock-ledger/", {"bucket": "IN_TRANSIT"}
        )
        assert all(row["bucket"] == "IN_TRANSIT" for row in rows(filtered))
        assert len(rows(filtered)) == 2  # ship in, receipt out

    def test_stock_adjustment_report(self, report_world):
        response = report_world.admin_client.get(f"{REPORTS}stock-adjustments/")
        row = only_row(response, adjustment_type="INCREASE")
        assert row["quantity"] == Decimal("1.00")
        assert row["reason"] == "Extra unit found in count."

    def test_user_activity_report(self, report_world):
        response = report_world.admin_client.get(f"{REPORTS}user-activity/")
        actions = {row["action"] for row in rows(response)}
        assert "CREATE" in actions
        assert "LOGIN" in actions

        filtered = report_world.admin_client.get(
            f"{REPORTS}user-activity/", {"action": "CREATE"}
        )
        assert {row["action"] for row in rows(filtered)} == {"CREATE"}


class TestValuation:
    def test_admin_only(self, report_world, auth_client):
        for key in ("stock-valuation-summary", "stock-valuation-detail"):
            for role in (User.Role.PURCHASE, User.Role.SALE, User.Role.VIEWER):
                assert auth_client(role).get(f"{REPORTS}{key}/").status_code == 403, (key, role)
            assert report_world.admin_client.get(f"{REPORTS}{key}/").status_code == 200

    def test_summary_totals(self, report_world):
        response = report_world.admin_client.get(f"{REPORTS}stock-valuation-summary/")
        # Phone 1680 + laptop 900 (18 @ carrying average 50).
        assert response.data["totals"]["Total company stock worth (AED)"] == Decimal("2580.00")
        sections = {section["title"]: section for section in response.data["sections"]}
        buckets = {row["bucket"]: row["value"] for row in sections["Worth by Bucket"]["rows"]}
        assert buckets["Physical"] == Decimal("1860.00")  # 480 + 480 + 900
        assert buckets["Pending"] == Decimal("480.00")
        assert buckets["In transit"] == Decimal("240.00")
        top = sections["Top Products by Value"]["rows"]
        assert top[0]["product"] == "iPhone 15 Pro 256GB"

    def test_detail_weighted_average(self, report_world):
        response = report_world.admin_client.get(f"{REPORTS}stock-valuation-detail/")
        sydney_phone = only_row(response, location="Sydney", product="iPhone 15 Pro")
        # (2 physical @ 240) + (2 pending @ 240) → avg unit cost 240.
        assert sydney_phone["avg_unit_cost"] == Decimal("240.00")
        assert sydney_phone["physical_value"] == Decimal("480.00")
        assert sydney_phone["pending_value"] == Decimal("480.00")
        assert sydney_phone["total_value"] == Decimal("960.00")

    def test_valuation_matches_rebuilt_balances(self, report_world):
        """The valuation total must survive a full ledger rebuild (drift check)."""
        before = report_world.admin_client.get(f"{REPORTS}stock-valuation-summary/").data
        assert rebuild_stock_balances() == []
        after = report_world.admin_client.get(f"{REPORTS}stock-valuation-summary/").data
        assert before["totals"] == after["totals"]

    def test_detail_cutoff_snapshot(self, report_world):
        response = report_world.admin_client.get(
            f"{REPORTS}stock-valuation-detail/",
            {"cutoff": report_world.mid_cutoff.isoformat()},
        )
        sydney_phone = only_row(response, location="Sydney", product="iPhone 15 Pro")
        # Before the shipment: 5 physical @ 240.
        assert sydney_phone["physical_qty"] == Decimal("5.00")
        assert sydney_phone["physical_value"] == Decimal("1200.00")
