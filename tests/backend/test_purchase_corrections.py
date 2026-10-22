"""Corrections of received, unsold stock and protected downstream workflows."""

from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Event
from time import monotonic, sleep

import pytest
from django.db import close_old_connections, connection, connections
from django.db.models import Case, DecimalField, F, Sum, When
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.audits.models import AuditLog
from apps.inventory.models import Bucket, StockBalance, StockLedgerEntry, TxnType
from apps.masterdata.models import Customer
from apps.products.models import Product
from apps.purchases.models import PurchaseCollection, PurchaseLine

pytestmark = pytest.mark.django_db
BASE = "/api/v1/purchases/"


def edit_payload(body):
    return {
        **{
            key: body[key]
            for key in ("invoice_no", "purchase_date", "location", "supplier", "notes")
        },
        "lines": [
            {
                key: line[key]
                for key in (
                    "id",
                    "product",
                    "quantity",
                    "unit_price",
                    "currency",
                    "exchange_rate",
                    "gst_rate_percent",
                    "notes",
                )
            }
            for line in body["lines"]
        ],
    }


def balance(product, location, bucket):
    obj = StockBalance.objects.filter(
        product=product, location=location, bucket=bucket
    ).first()
    return (obj.quantity, obj.value_aed) if obj else (Decimal("0"), Decimal("0"))


def assert_reconciled():
    # Comparison only: repairing the balance would mask an incorrect operation.
    rows = StockLedgerEntry.objects.values(
        "product_id", "location_id", "bucket"
    ).annotate(
        qty=Sum(F("qty_in") - F("qty_out")),
        value=Sum(
            Case(
                When(qty_in__gt=0, then=F("aed_value")),
                default=-F("aed_value"),
                output_field=DecimalField(),
            )
        ),
    )
    expected = {
        (r["product_id"], r["location_id"], r["bucket"]): (r["qty"], r["value"])
        for r in rows
    }
    for obj in StockBalance.objects.all():
        assert (obj.quantity, obj.value_aed) == expected.pop(
            (obj.product_id, obj.location_id, obj.bucket),
            (0, 0),
        )
    assert not expected


@pytest.mark.parametrize("remove", [False, True])
def test_current_reports_follow_corrected_product_cost_and_removal(samples, masterdata, remove):
    client, body = samples("4")
    target = Product.objects.create(name="Correct report SKU", category=masterdata.phone.category)
    data = edit_payload(body)
    if remove:
        data["lines"] = data["lines"][1:]
    else:
        data["lines"][0].update(product=target.pk, unit_price="120.00")
    response = client.put(f"{BASE}{body['id']}/", data, format="json")
    assert response.status_code == 200, response.data

    def report(key):
        response = client.get(f"/api/v1/reports/{key}/")
        assert response.status_code == 200, response.data
        return response.data

    for key in ("purchase-report", "pending-purchase-stock", "gst-report"):
        rows = report(key)["sections"][0]["rows"]
        assert len(rows) == (1 if remove else 2), (key, rows)
        assert not any(row["product"] == masterdata.phone.name for row in rows)
        if not remove:
            corrected = next(row for row in rows if row["product"] == target.name)
            if key == "purchase-report":
                assert corrected["unit_price_aed"] == Decimal("288.00")
                assert corrected["collected_qty"] == Decimal("4.00")
            elif key == "pending-purchase-stock":
                assert corrected["pending_qty"] == Decimal("6.00")
                assert corrected["aed_value_pending"] == Decimal("1728.00")
            else:
                assert corrected["net_gst"] == Decimal("109.09")
    summary = report("stock-valuation-summary")
    assert summary["totals"]["Total company stock worth (AED)"] == Decimal(
        "240.00" if remove else "3120.00"
    )
    if not remove:
        detail = report("stock-valuation-detail")["sections"][0]["rows"]
        corrected = next(row for row in detail if row["product"] == target.name)
        assert corrected["physical_value"] == Decimal("1152.00")
        assert corrected["pending_value"] == Decimal("1728.00")
        assert corrected["avg_unit_cost"] == Decimal("288.00")
    assert_reconciled()


@pytest.fixture
def samples(auth_client, masterdata):
    def create(
        collected="4",
        *,
        later=False,
        role=User.Role.ADMIN,
        quantity="10",
        price="100",
        exchange_rate="2.4",
        keeper_collected="0",
    ):
        client = auth_client(role)
        response = client.post(
            BASE,
            {
                "invoice_no": "INV-CORRECTION",
                "purchase_date": "2026-07-01",
                "location": masterdata.sydney.pk,
                "supplier": masterdata.supplier.pk,
                "lines": [
                    {
                        "product": masterdata.phone.pk,
                        "quantity": quantity,
                        "unit_price": price,
                        "currency": masterdata.aud.pk,
                        "exchange_rate": exchange_rate,
                        "collected_qty": "0" if later else collected,
                    },
                    {
                        "product": masterdata.laptop.pk,
                        "quantity": "2",
                        "unit_price": "50",
                        "currency": masterdata.aud.pk,
                        "collected_qty": keeper_collected,
                    },
                ],
            },
            format="json",
        )
        assert response.status_code == 201, response.data
        purchase_id = response.data["id"]
        if later and Decimal(collected):
            response = client.post(
                f"{BASE}{purchase_id}/collections/",
                {
                    "collection_date": "2026-07-02",
                    "lines": [
                        {
                            "purchase_line": response.data["lines"][0]["id"],
                            "quantity": collected,
                        }
                    ],
                },
                format="json",
            )
            assert response.status_code == 201, response.data
        body = client.get(f"{BASE}{purchase_id}/").data
        return client, body

    return create


@pytest.mark.parametrize("role", [User.Role.ADMIN, User.Role.PURCHASE])
@pytest.mark.parametrize(
    "collected,later",
    [("0", False), ("4", False), ("10", False), ("4", True), ("10", True)],
)
@pytest.mark.parametrize("operation", ["product", "unit_price", "remove"])
def test_unsold_corrections_keep_stock_and_history_consistent(
    samples,
    masterdata,
    role,
    collected,
    later,
    operation,
):
    client, body = samples(collected, later=later, role=role)
    original = list(StockLedgerEntry.objects.order_by("pk").values())
    collection_ids = list(PurchaseCollection.objects.values_list("pk", flat=True))
    data = edit_payload(body)
    target = masterdata.phone
    if operation == "product":
        target = Product.objects.create(
            name="Corrected Phone", category=masterdata.phone.category
        )
        data["lines"][0]["product"] = target.pk
    elif operation == "unit_price":
        data["lines"][0]["unit_price"] = "120.00"
    else:
        data["lines"] = data["lines"][1:]
    response = client.put(f"{BASE}{body['id']}/", data, format="json")
    assert response.status_code == 200, response.data
    assert (
        list(
            StockLedgerEntry.objects.filter(pk__in=[e["id"] for e in original])
            .order_by("pk")
            .values()
        )
        == original
    )
    assert (
        list(PurchaseCollection.objects.values_list("pk", flat=True)) == collection_ids
    )
    physical = Decimal(collected)
    pending = 10 - physical
    if operation == "remove":
        assert len(response.data["lines"]) == 1
        assert PurchaseLine.objects.get(pk=body["lines"][0]["id"]).is_deleted
        assert balance(target, masterdata.sydney, Bucket.PHYSICAL) == (0, 0)
        assert balance(target, masterdata.sydney, Bucket.PENDING) == (0, 0)
    else:
        cost = Decimal("288") if operation == "unit_price" else Decimal("240")
        assert balance(target, masterdata.sydney, Bucket.PHYSICAL) == (
            physical,
            physical * cost,
        )
        assert balance(target, masterdata.sydney, Bucket.PENDING) == (
            pending,
            pending * cost,
        )
        if operation == "product":
            assert balance(masterdata.phone, masterdata.sydney, Bucket.PHYSICAL) == (
                0,
                0,
            )
            assert balance(masterdata.phone, masterdata.sydney, Bucket.PENDING) == (
                0,
                0,
            )
        line = response.data["lines"][0]
        assert line["collected"] == f"{physical:.2f}"
        assert line["can_correct"] is True
        if operation == "unit_price":
            assert line["total_value_aed"] == "2880.00"
            assert line["gst_amount_aed"] == "261.82"
    audit = AuditLog.objects.filter(
        module="purchases", action="UPDATE", record_id=body["id"]
    ).latest("id")
    assert audit.before_values["lines"][0]["product"].startswith("iPhone")
    assert_reconciled()


def test_repeated_product_price_corrections_and_collection_undo(samples, masterdata):
    client, body = samples("4")
    first_collection = PurchaseCollection.objects.get()
    target = Product.objects.create(
        name="Corrected Phone", category=masterdata.phone.category
    )
    original_ledger_count = StockLedgerEntry.objects.count()
    for price in ["120.00", "130.00", "110.00"]:
        data = edit_payload(body)
        data["lines"][0].update(product=target.pk, unit_price=price)
        result = client.put(f"{BASE}{body['id']}/", data, format="json")
        assert result.status_code == 200, result.data
        body = result.data
        assert_reconciled()
    # Reversal/replay grows linearly rather than reversing every historical row.
    assert StockLedgerEntry.objects.count() <= original_ledger_count + 3 * 6
    collected = client.post(
        f"{BASE}{body['id']}/collections/",
        {
            "collection_date": "2026-07-03",
            "lines": [{"purchase_line": body["lines"][0]["id"], "quantity": "6"}],
        },
        format="json",
    )
    assert collected.status_code == 201, collected.data
    assert balance(target, masterdata.sydney, Bucket.PHYSICAL) == (10, 2640)
    undo = client.delete(f"{BASE}{body['id']}/collections/{first_collection.pk}/")
    assert undo.status_code == 204, undo.data
    assert balance(target, masterdata.sydney, Bucket.PHYSICAL) == (6, 1584)
    assert balance(target, masterdata.sydney, Bucket.PENDING) == (4, 1056)
    assert balance(masterdata.phone, masterdata.sydney, Bucket.PHYSICAL) == (0, 0)
    assert_reconciled()


def test_removal_does_not_resurrect_stock_when_shared_collection_is_undone(
    samples, masterdata
):
    client, body = samples("4", keeper_collected="1")
    collection = PurchaseCollection.objects.get()
    data = edit_payload(body)
    data["lines"] = data["lines"][1:]
    response = client.put(f"{BASE}{body['id']}/", data, format="json")
    assert response.status_code == 200, response.data
    undo = client.delete(f"{BASE}{body['id']}/collections/{collection.pk}/")
    assert undo.status_code == 204, undo.data
    assert balance(masterdata.phone, masterdata.sydney, Bucket.PHYSICAL) == (0, 0)
    assert balance(masterdata.phone, masterdata.sydney, Bucket.PENDING) == (0, 0)
    assert balance(masterdata.laptop, masterdata.sydney, Bucket.PHYSICAL) == (0, 0)
    assert balance(masterdata.laptop, masterdata.sydney, Bucket.PENDING) == (2, 240)
    assert_reconciled()


def test_multi_location_collection_costs_and_rounding_remain_exact(samples, masterdata):
    client, body = samples("2", quantity="7", price="0.03", exchange_rate="1.123456")
    collection = client.post(
        f"{BASE}{body['id']}/collections/",
        {
            "collection_date": "2026-07-02",
            "location": masterdata.dubai.pk,
            "lines": [{"purchase_line": body["lines"][0]["id"], "quantity": "3"}],
        },
        format="json",
    )
    assert collection.status_code == 201, collection.data
    data = edit_payload(body)
    data["lines"][0]["unit_price"] = "0.05"
    result = client.put(f"{BASE}{body['id']}/", data, format="json")
    assert result.status_code == 200, result.data
    total = sum(
        balance(masterdata.phone, location, bucket)[1]
        for location, bucket in [
            (masterdata.sydney, Bucket.PENDING),
            (masterdata.sydney, Bucket.PHYSICAL),
            (masterdata.dubai, Bucket.PHYSICAL),
        ]
    )
    assert (
        total == Decimal(result.data["lines"][0]["total_value_aed"]) == Decimal("0.39")
    )
    assert balance(masterdata.phone, masterdata.sydney, Bucket.PHYSICAL)[0] == 2
    assert balance(masterdata.phone, masterdata.dubai, Bucket.PHYSICAL)[0] == 3
    assert_reconciled()


def test_refund_and_parent_delete_after_correction_use_corrected_cost(
    samples, masterdata
):
    client, body = samples("4")
    data = edit_payload(body)
    data["lines"][0]["unit_price"] = "120"
    response = client.put(f"{BASE}{body['id']}/", data, format="json")
    assert response.status_code == 200, response.data
    refund = client.post(
        f"{BASE}{body['id']}/refunds/",
        {
            "refund_date": "2026-07-02",
            "reason": "Return one corrected unit",
            "lines": [
                {
                    "purchase_line": body["lines"][0]["id"],
                    "source": "RECEIVED",
                    "quantity": "1",
                }
            ],
        },
        format="json",
    )
    assert refund.status_code == 201, refund.data
    assert refund.data["lines"][0]["value_reversal_aed"] == "288.00"
    assert refund.data["lines"][0]["gst_reversal_aed"] == "26.18"
    assert balance(masterdata.phone, masterdata.sydney, Bucket.PHYSICAL) == (3, 864)
    undo = client.delete(f"{BASE}{body['id']}/refunds/{refund.data['id']}/")
    assert undo.status_code == 204
    result = client.delete(f"{BASE}{body['id']}/")
    assert result.status_code == 204, result.data
    for obj in StockBalance.objects.all():
        assert obj.quantity == obj.value_aed == 0
    assert_reconciled()


def add_dependency(client, body, world, kind):
    if kind in {"shipment", "draft"}:
        return client.post(
            "/api/v1/shipments/",
            {
                "shipment_date": "2026-07-02",
                "from_location": world.sydney.pk,
                "to_location": world.dubai.pk,
                "ship": kind == "shipment",
                "lines": [{"product": world.phone.pk, "quantity": "1"}],
            },
            format="json",
        )
    if kind == "refund":
        return client.post(
            f"{BASE}{body['id']}/refunds/",
            {
                "refund_date": "2026-07-02",
                "reason": "Sample pending cancellation",
                "lines": [
                    {
                        "purchase_line": body["lines"][0]["id"],
                        "source": "PENDING",
                        "quantity": "1",
                    }
                ],
            },
            format="json",
        )
    if kind == "adjustment":
        return client.post(
            "/api/v1/stock-adjustments/",
            {
                "adjustment_date": "2026-07-02",
                "product": world.phone.pk,
                "location": world.sydney.pk,
                "adjustment_type": "DECREASE",
                "quantity": "1",
                "reason": "Synthetic adjustment",
            },
            format="json",
        )
    world.sydney.is_sales_location = True
    world.sydney.save()
    customer = Customer.objects.create(name="Synthetic customer")
    return client.post(
        "/api/v1/sales/",
        {
            "sale_date": "2026-07-02",
            "location": world.sydney.pk,
            "customer": customer.pk,
            "lines": [{"product": world.phone.pk, "quantity": "1"}],
        },
        format="json",
    )


@pytest.mark.parametrize("kind", ["sale", "shipment", "draft", "refund", "adjustment"])
@pytest.mark.parametrize("operation", ["product", "unit_price", "remove"])
def test_dependent_line_is_blocked_with_reason_and_transaction_rollback(
    samples,
    masterdata,
    kind,
    operation,
):
    client, body = samples("4")
    dependency = add_dependency(client, body, masterdata, kind)
    assert dependency.status_code == 201, dependency.data
    fresh = client.get(f"{BASE}{body['id']}/").data
    assert fresh["lines"][0]["can_correct"] is False
    assert fresh["lines"][0]["correction_block_reason"]
    assert fresh["lines"][1]["can_correct"] is True
    data = edit_payload(fresh)
    data["notes"] = "Must roll back with rejected correction"
    if operation == "remove":
        data["lines"] = data["lines"][1:]
    else:
        data["lines"][0][operation] = (
            masterdata.laptop.pk if operation == "product" else "120"
        )
    ledger_before = list(StockLedgerEntry.objects.order_by("pk").values())
    audits_before = AuditLog.objects.count()
    response = client.put(f"{BASE}{body['id']}/", data, format="json")
    assert response.status_code == 400, response.data
    assert client.get(f"{BASE}{body['id']}/").data == fresh
    assert list(StockLedgerEntry.objects.order_by("pk").values()) == ledger_before
    assert AuditLog.objects.count() == audits_before
    assert_reconciled()


def test_other_product_can_be_corrected_while_dependent_line_is_unchanged(
    samples, masterdata
):
    client, body = samples("4", keeper_collected="1")
    assert add_dependency(client, body, masterdata, "shipment").status_code == 201
    data = edit_payload(body)
    data["lines"][1]["unit_price"] = "60"
    response = client.put(f"{BASE}{body['id']}/", data, format="json")
    assert response.status_code == 200, response.data
    assert balance(masterdata.laptop, masterdata.sydney, Bucket.PHYSICAL) == (1, 144)
    assert balance(masterdata.laptop, masterdata.sydney, Bucket.PENDING) == (1, 144)
    assert_reconciled()


@pytest.mark.parametrize("role", [User.Role.SALE, User.Role.VIEWER])
def test_correction_permissions_are_unchanged(samples, auth_client, role):
    _client, body = samples("4")
    data = edit_payload(body)
    data["lines"][0]["unit_price"] = "120"
    response = auth_client(role).put(f"{BASE}{body['id']}/", data, format="json")
    assert response.status_code == 403


def test_empty_or_duplicate_line_updates_are_rejected(samples):
    client, body = samples("4")
    data = edit_payload(body)
    data["lines"] = []
    assert client.put(f"{BASE}{body['id']}/", data, format="json").status_code == 400
    data = edit_payload(body)
    data["lines"].append(deepcopy(data["lines"][0]))
    assert client.put(f"{BASE}{body['id']}/", data, format="json").status_code == 400


@pytest.mark.parametrize(
    "field,value",
    [("currency", "aed"), ("exchange_rate", "2.5"), ("gst_rate_percent", "15")],
)
def test_other_frozen_fields_stay_locked_in_first_release(
    samples, masterdata, field, value
):
    client, body = samples("4")
    data = edit_payload(body)
    data["lines"][0][field] = masterdata.aed.pk if value == "aed" else value
    response = client.put(f"{BASE}{body['id']}/", data, format="json")
    assert response.status_code == 400
    assert "remain fixed after collection" in str(response.data)


def _thread_request(user_id, method, url, payload):
    close_old_connections()
    try:
        client = APIClient()
        client.force_authenticate(User.objects.get(pk=user_id))
        return getattr(client, method)(url, payload, format="json")
    finally:
        connections.close_all()


def _wait_for_stock_lock_waiter():
    deadline = monotonic() + 5
    while monotonic() < deadline:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM pg_locks WHERE locktype = 'advisory' AND NOT granted "
                "AND database = (SELECT oid FROM pg_database WHERE datname = current_database())"
            )
            if cursor.fetchone()[0]:
                return
        sleep(0.01)
    raise AssertionError(
        "The competing request did not wait for the stock transaction lock."
    )


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("first", ["sale", "correction"])
def test_sale_and_correction_serialize_eligibility_and_costing(
    samples, masterdata, monkeypatch, first
):
    from apps.purchases import corrections
    from apps.sales import services as sale_services

    client, body = samples("4")
    masterdata.sydney.is_sales_location = True
    masterdata.sydney.save()
    customer = Customer.objects.create(name="Concurrent sample customer")
    held, release = Event(), Event()
    module = sale_services if first == "sale" else corrections
    original_post = module.post_event

    def paused_post(**kwargs):
        if not held.is_set():
            held.set()
            assert release.wait(8), "Test did not release the held stock operation."
        return original_post(**kwargs)

    monkeypatch.setattr(module, "post_event", paused_post)
    data = edit_payload(body)
    data["lines"][0]["unit_price"] = "120"
    sale = {
        "sale_date": "2026-07-02",
        "location": masterdata.sydney.pk,
        "customer": customer.pk,
        "lines": [{"product": masterdata.phone.pk, "quantity": "1"}],
    }
    requests = {
        "sale": (client.user.pk, "post", "/api/v1/sales/", sale),
        "correction": (client.user.pk, "put", f"{BASE}{body['id']}/", data),
    }
    second = "correction" if first == "sale" else "sale"
    with ThreadPoolExecutor(max_workers=2) as pool:
        first_future = pool.submit(_thread_request, *requests[first])
        try:
            assert held.wait(8), (
                "First operation did not reach the serialized posting step."
            )
            second_future = pool.submit(_thread_request, *requests[second])
            _wait_for_stock_lock_waiter()
        finally:
            release.set()
        results = {
            first: first_future.result(timeout=10),
            second: second_future.result(timeout=10),
        }

    assert results["sale"].status_code == 201, results["sale"].data
    assert results["correction"].status_code == (400 if first == "sale" else 200)
    if first == "sale":
        assert "sale" in str(results["correction"].data)
        assert balance(masterdata.phone, masterdata.sydney, Bucket.PHYSICAL) == (3, 720)
    else:
        assert balance(masterdata.phone, masterdata.sydney, Bucket.PHYSICAL) == (3, 864)
        assert StockLedgerEntry.objects.get(txn_type=TxnType.SALE).aed_value == 288
    assert_reconciled()
