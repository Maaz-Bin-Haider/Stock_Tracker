"""Search/filter results, computed invoice statuses, and whole-result totals."""

from decimal import Decimal

import pytest

from apps.accounts.models import User
from apps.masterdata.models import Supplier
from apps.products.models import Product
from apps.purchases.models import Purchase, PurchaseStatus

pytestmark = pytest.mark.django_db
URL = "/api/v1/purchases/"


@pytest.fixture
def search_world(admin_client, masterdata):
    def create(reference, *, quantity="10", collected="0", date="2026-10-22", **extra):
        payload = {
            "invoice_no": reference, "purchase_date": date,
            "location": masterdata.sydney.pk, "supplier": masterdata.supplier.pk,
            "notes": "Blue shipment reference",
            "lines": [{"product": masterdata.phone.pk, "quantity": quantity,
                       "unit_price": "100", "currency": masterdata.aud.pk,
                       "collected_qty": collected}],
        }
        payload.update(extra)
        response = admin_client.post(URL, payload, format="json")
        assert response.status_code == 201, response.data
        return response.data
    return create


def assert_result(client, params, references):
    response = client.get(URL, params)
    assert response.status_code == 200, response.data
    assert {row["invoice_no"] for row in response.data["results"]} == set(references)
    assert response.data["count"] == len(references)
    return response.data


def test_combined_filters_and_totals_include_whole_invoices(admin_client, masterdata, search_world):
    supplier = Supplier.objects.create(name="Different supplier")
    search_world("MATCH", collected="4")
    search_world("OLD", date="2026-09-01")
    search_world("OTHER", supplier=supplier.pk)
    data = assert_result(admin_client, {
        "search": "iPhone 256GB", "search_in": "product",
        "status": "PARTIALLY_RECEIVED", "supplier": masterdata.supplier.pk,
        "location": masterdata.sydney.pk, "product": masterdata.phone.pk,
        "date_from": "2026-10-22", "date_to": "2026-10-22",
    }, ["MATCH"])
    assert Decimal(data["totals"]["total_quantity"]) == 10
    assert Decimal(data["totals"]["total_pending"]) == 6
    assert Decimal(data["totals"]["total_value_aed"]) == 2400


@pytest.mark.parametrize("scope,term", [
    ("invoice", "MATCH"), ("product", "256GB"), ("product", "PHONE-SKU"),
    ("supplier", "Distributor"), ("location", "Sydney"), ("notes", "Blue"),
    ("all", "iPhone 256GB"),
])
def test_scoped_search(admin_client, masterdata, search_world, scope, term):
    masterdata.phone.sku = "PHONE-SKU"
    masterdata.phone.save()
    search_world("MATCH")
    assert_result(admin_client, {"search_in": scope, "search": term}, ["MATCH"])
    assert_result(admin_client, {"search_in": "invoice", "search": "256GB"}, [])


def test_removed_product_and_duplicate_matches_do_not_leak(admin_client, masterdata, search_world):
    other = Product.objects.create(name="Retained laptop", category=masterdata.phone.category)
    body = search_world("MATCH", lines=[
        {"product": masterdata.phone.pk, "quantity": "2", "unit_price": "100", "currency": masterdata.aud.pk},
        {"product": masterdata.phone.pk, "quantity": "3", "unit_price": "100", "currency": masterdata.aud.pk},
        {"product": other.pk, "quantity": "1", "unit_price": "50", "currency": masterdata.aud.pk},
    ])
    data = assert_result(admin_client, {"search": "iPhone"}, ["MATCH"])
    assert Decimal(data["totals"]["total_quantity"]) == 6
    Purchase.objects.get(pk=body["id"]).lines.filter(product=masterdata.phone).update(is_deleted=True)
    assert_result(admin_client, {"search": "iPhone"}, [])
    assert_result(admin_client, {"product": masterdata.phone.pk}, [])
    assert_result(admin_client, {"search": "Retained"}, ["MATCH"])


def test_product_words_must_match_same_line(admin_client, masterdata, search_world):
    other = Product.objects.create(name="Laptop", storage_specs="1TB", category=masterdata.phone.category)
    search_world("MATCH", lines=[
        {"product": masterdata.phone.pk, "quantity": "1", "unit_price": "100", "currency": masterdata.aud.pk},
        {"product": other.pk, "quantity": "1", "unit_price": "100", "currency": masterdata.aud.pk},
    ])
    assert_result(admin_client, {"search_in": "product", "search": "iPhone 1TB"}, [])


def test_status_filters_match_computed_status_with_mixed_refunds(admin_client, masterdata, search_world):
    search_world("PENDING")
    search_world("PARTIAL", collected="4")
    search_world("FULL", collected="10")
    cancel = search_world("CANCEL")
    returned = search_world("RETURN", collected="10")
    mixed = search_world("MIXED", lines=[
        {"product": masterdata.phone.pk, "quantity": "2", "collected_qty": "2", "unit_price": "100", "currency": masterdata.aud.pk},
        {"product": masterdata.laptop.pk, "quantity": "2", "unit_price": "50", "currency": masterdata.aud.pk},
    ])
    full_cancel = search_world("FULL-AND-CANCEL", lines=[
        {"product": masterdata.phone.pk, "quantity": "2", "collected_qty": "2", "unit_price": "100", "currency": masterdata.aud.pk},
        {"product": masterdata.laptop.pk, "quantity": "2", "unit_price": "50", "currency": masterdata.aud.pk},
    ])
    for body, line_index, source, quantity in [
        (cancel, 0, "PENDING", "10"), (returned, 0, "RECEIVED", "10"),
        (mixed, 0, "RECEIVED", "2"), (mixed, 1, "PENDING", "2"),
        (full_cancel, 1, "PENDING", "2"),
    ]:
        response = admin_client.post(f"{URL}{body['id']}/refunds/", {
            "refund_date": "2026-10-22", "reason": "Synthetic status test",
            "lines": [{"purchase_line": body["lines"][line_index]["id"], "source": source,
                       "quantity": quantity, "location": masterdata.sydney.pk}],
        }, format="json")
        assert response.status_code == 201, response.data
    # Include legacy empty invoices; no new API write permits creating one.
    Purchase.objects.create(invoice_no="EMPTY", purchase_date="2026-10-22",
                            supplier=masterdata.supplier, location=masterdata.sydney)
    for status in PurchaseStatus.values:
        expected = [obj.invoice_no for obj in Purchase.objects.all() if obj.status == status]
        body = assert_result(admin_client, {"status": status}, expected)
        assert all(row["status"] == status for row in body["results"])


@pytest.mark.parametrize("params", [
    {"status": "INVALID"}, {"search_in": "INVALID"}, {"date_from": "bad"},
    {"date_from": "2026-10-23", "date_to": "2026-10-22"}, {"product": "bad"},
])
def test_invalid_filters_return_clear_400(admin_client, params):
    assert admin_client.get(URL, params).status_code == 400


def test_totals_and_ordering_across_pages(admin_client, masterdata, search_world):
    body = search_world("SEED")
    source = Purchase.objects.get(pk=body["id"])
    # Page boundary and equal dates/references: ordering needs a stable id tie-break.
    for index in range(51):
        clone = Purchase.objects.create(invoice_no=f"PAGE-{index:02}", purchase_date=source.purchase_date,
                                       supplier=source.supplier, location=source.location)
        line = source.lines.first()
        line.pk = None
        line.purchase = clone
        line.save()
    first = admin_client.get(URL, {"search": "PAGE", "ordering": "purchase_date"}).data
    second = admin_client.get(URL, {"search": "PAGE", "ordering": "purchase_date", "page": 2}).data
    assert first["count"] == second["count"] == 51
    assert len(first["results"]) == 50 and len(second["results"]) == 1
    assert not ({r["id"] for r in first["results"]} & {r["id"] for r in second["results"]})
    assert Decimal(first["totals"]["total_quantity"]) == Decimal(second["totals"]["total_quantity"]) == 510


@pytest.mark.parametrize("role", [User.Role.ADMIN, User.Role.PURCHASE, User.Role.SALE, User.Role.VIEWER])
def test_all_roles_can_filter_read_only(auth_client, search_world, role):
    search_world("READ")
    assert_result(auth_client(role), {"search": "READ", "status": "PENDING"}, ["READ"])
