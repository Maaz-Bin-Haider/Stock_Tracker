"""Every ledger row must name the one record it came from.

``source_module`` is the owning app, and several record types live in each one,
so ``purchases#3`` matched purchase 3, collection 3 and refund 3 — records that
routinely share ids because each table numbers from 1. ``txn_type`` separated
most rows but not the reversals: deleting a purchase, a collection or a refund
all post DELETE_REVERSAL in the purchases module.
"""

from decimal import Decimal

import pytest
from django.db import connection

from apps.accounts.models import User
from apps.inventory.models import SourceType, StockLedgerEntry, TxnType
from apps.inventory.services import Movement, PostingError, post_event
from apps.purchases.models import Purchase, PurchaseCollection, PurchaseRefund
from apps.sales.models import Sale
from apps.shipments.models import Shipment, ShipmentReceipt

pytestmark = pytest.mark.django_db

# What each source_type promises source_id points at.
MODELS = {
    SourceType.PURCHASE: Purchase,
    SourceType.PURCHASE_COLLECTION: PurchaseCollection,
    SourceType.PURCHASE_REFUND: PurchaseRefund,
    SourceType.SHIPMENT: Shipment,
    SourceType.SHIPMENT_RECEIPT: ShipmentReceipt,
    SourceType.SALE: Sale,
}


def _next_collection_takes_id(target_id):
    """Make the next collection row take ``target_id``.

    In production both tables number from 1, so a purchase and a collection
    share an id as a matter of course — 263 of 263 purchases did. Forcing it
    here states that condition outright instead of depending on the two
    sequences happening to line up, which is true only for the first records of
    a run and therefore varies with test order.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT setval(pg_get_serial_sequence('purchases_purchasecollection', 'id'), %s, false)",
            [target_id],
        )


def _purchase_with_collection(client, world):
    """An invoice plus a collection deliberately given the purchase's own id."""
    response = client.post(
        "/api/v1/purchases/",
        {
            "invoice_no": "INV-COLLIDE",
            "purchase_date": "2026-07-01",
            "location": world.sydney.pk,
            "supplier": world.supplier.pk,
            "lines": [
                {
                    "product": world.phone.pk,
                    "quantity": "10",
                    "unit_price": "100.00",
                    "currency": world.aud.pk,
                }
            ],
        },
        format="json",
    )
    assert response.status_code == 201, response.data
    purchase = Purchase.objects.get(pk=response.data["id"])

    _next_collection_takes_id(purchase.pk)
    collected = client.post(
        f"/api/v1/purchases/{purchase.pk}/collections/",
        {
            "collection_date": "2026-07-02",
            "location": world.sydney.pk,
            "lines": [{"purchase_line": response.data["lines"][0]["id"], "quantity": "4"}],
        },
        format="json",
    )
    assert collected.status_code == 201, collected.data
    return purchase, purchase.collections.get()


def test_a_purchase_and_its_collection_really_do_share_an_id(masterdata, auth_client):
    """The precondition for the bug — asserted so the tests below cannot quietly
    start passing for the wrong reason."""
    purchase, collection = _purchase_with_collection(auth_client(User.Role.PURCHASE), masterdata)

    assert purchase.pk == collection.pk


def test_source_type_separates_records_that_share_an_id(masterdata, auth_client):
    purchase, collection = _purchase_with_collection(auth_client(User.Role.PURCHASE), masterdata)

    # Addressing by module alone pulls in both records' rows.
    by_module = StockLedgerEntry.objects.filter(
        source_module="purchases", source_id=purchase.pk
    )
    assert {entry.txn_type for entry in by_module} == {
        TxnType.PURCHASE_ENTRY,
        TxnType.PURCHASE_COLLECTION,
    }

    # Addressing by source_type resolves to exactly one of them.
    entry_rows = StockLedgerEntry.objects.filter(
        source_type=SourceType.PURCHASE, source_id=purchase.pk
    )
    collection_rows = StockLedgerEntry.objects.filter(
        source_type=SourceType.PURCHASE_COLLECTION, source_id=collection.pk
    )
    assert {entry.txn_type for entry in entry_rows} == {TxnType.PURCHASE_ENTRY}
    assert {entry.txn_type for entry in collection_rows} == {TxnType.PURCHASE_COLLECTION}
    assert not set(entry_rows.values_list("id", flat=True)) & set(
        collection_rows.values_list("id", flat=True)
    )


def test_deleting_a_collection_leaves_the_purchases_own_rows_alone(masterdata, auth_client):
    """The reversal case txn_type could not separate: both a purchase delete and
    a collection delete post DELETE_REVERSAL in the purchases module."""
    client = auth_client(User.Role.PURCHASE)
    purchase, collection = _purchase_with_collection(client, masterdata)

    response = client.delete(
        f"/api/v1/purchases/{purchase.pk}/collections/{collection.pk}/"
    )
    assert response.status_code == 204

    reversals = StockLedgerEntry.objects.filter(txn_type=TxnType.DELETE_REVERSAL)
    assert reversals.exists()
    assert {entry.source_type for entry in reversals} == {SourceType.PURCHASE_COLLECTION}
    assert not StockLedgerEntry.objects.filter(
        source_type=SourceType.PURCHASE, txn_type=TxnType.DELETE_REVERSAL
    ).exists()


def test_every_row_of_a_full_business_history_resolves_to_one_live_record(report_world):
    """report_world exercises purchases, collection, refunds, shipment, receipt,
    sales and an adjustment — every posting path in the system."""
    entries = StockLedgerEntry.objects.all()
    assert entries.count() > 0

    for entry in entries:
        assert entry.source_type, f"row {entry.id} carries no source_type"
        model = MODELS.get(entry.source_type)
        if model is None:  # stock adjustments live in inventory
            from apps.inventory.models import StockAdjustment

            model = StockAdjustment
        assert model.objects.filter(pk=entry.source_id).exists(), (
            f"row {entry.id} points at a missing "
            f"{entry.source_type}#{entry.source_id}"
        )


def test_posting_without_a_usable_source_type_is_refused(masterdata):
    """The ledger is append-only, so a row that cannot be traced back can never
    be repaired in place — refuse it at the door instead."""
    move = Movement(
        product=masterdata.phone,
        location=masterdata.dubai,
        bucket="PHYSICAL",
        qty_in=Decimal("1"),
    )
    for bad in ("", "purchases", "NOT_A_TYPE"):
        with pytest.raises(PostingError):
            post_event(
                txn_type=TxnType.ADJUSTMENT,
                source_module="tests",
                source_type=bad,
                source_id=1,
                movements=[move],
            )
    assert not StockLedgerEntry.objects.exists()


def test_the_ledger_report_reference_names_the_record_type(report_world):
    """The Stock Ledger Report's reference column is the human-facing form of
    this address; "purchases#3" was ambiguous on the page too."""
    from apps.reports.builders import REPORTS

    result = REPORTS["stock-ledger"].build({}, True)
    references = {row["reference"] for row in result.sections[0].rows}

    assert references
    assert not any(reference.startswith("purchases#") for reference in references)
    assert any(reference.startswith("purchase#") for reference in references)
    assert any(reference.startswith("purchase_collection#") for reference in references)
