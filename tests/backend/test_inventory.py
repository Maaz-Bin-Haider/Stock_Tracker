"""post_event / balances / rebuild tests (TECHNICAL_ARCHITECTURE §5.3-§5.4)."""

from decimal import Decimal

import pytest

from apps.inventory.models import Bucket, StockBalance, StockLedgerEntry, TxnType
from apps.inventory.services import (
    Movement,
    NegativeStockError,
    PostingError,
    post_event,
    rebuild_stock_balances,
    reversal_movements,
)

pytestmark = pytest.mark.django_db


def balance(product, location, bucket):
    row = StockBalance.objects.filter(product=product, location=location, bucket=bucket).first()
    return (row.quantity, row.value_aed) if row else (Decimal("0"), Decimal("0"))


def test_movement_requires_exactly_one_direction(masterdata):
    with pytest.raises(PostingError):
        Movement(product=masterdata.phone, location=masterdata.sydney, bucket=Bucket.PHYSICAL)
    with pytest.raises(PostingError):
        Movement(
            product=masterdata.phone,
            location=masterdata.sydney,
            bucket=Bucket.PHYSICAL,
            qty_in=Decimal("1"),
            qty_out=Decimal("1"),
        )


def test_post_event_writes_ledger_and_balance(masterdata):
    posted = post_event(
        txn_type=TxnType.ADJUSTMENT,
        source_module="tests",
        source_id=1,
        movements=[
            Movement(
                product=masterdata.phone,
                location=masterdata.sydney,
                bucket=Bucket.PHYSICAL,
                qty_in=Decimal("10"),
                aed_value=Decimal("100.00"),
            )
        ],
    )
    assert len(posted.entries) == 1
    assert balance(masterdata.phone, masterdata.sydney, Bucket.PHYSICAL) == (
        Decimal("10.00"),
        Decimal("100.00"),
    )


def test_negative_physical_requires_confirmation(masterdata):
    move = Movement(
        product=masterdata.phone,
        location=masterdata.dubai,
        bucket=Bucket.PHYSICAL,
        qty_out=Decimal("5"),
        aed_value=Decimal("50.00"),
    )
    with pytest.raises(NegativeStockError):
        post_event(
            txn_type=TxnType.ADJUSTMENT, source_module="tests", source_id=2, movements=[move]
        )
    # Nothing was written (SRS §7.3: all-or-nothing).
    assert StockLedgerEntry.objects.count() == 0
    assert balance(masterdata.phone, masterdata.dubai, Bucket.PHYSICAL)[0] == 0

    post_event(
        txn_type=TxnType.ADJUSTMENT,
        source_module="tests",
        source_id=2,
        movements=[move],
        confirm_negative=True,
    )
    assert balance(masterdata.phone, masterdata.dubai, Bucket.PHYSICAL) == (
        Decimal("-5.00"),
        Decimal("-50.00"),
    )


def test_reversal_movements_exactly_undo(masterdata):
    posted = post_event(
        txn_type=TxnType.ADJUSTMENT,
        source_module="tests",
        source_id=3,
        movements=[
            Movement(
                product=masterdata.phone,
                location=masterdata.sydney,
                bucket=Bucket.PENDING,
                qty_in=Decimal("7"),
                aed_value=Decimal("70.00"),
                gst_value=Decimal("7.00"),
            )
        ],
    )
    post_event(
        txn_type=TxnType.DELETE_REVERSAL,
        source_module="tests",
        source_id=3,
        movements=reversal_movements(posted.entries),
    )
    assert balance(masterdata.phone, masterdata.sydney, Bucket.PENDING) == (
        Decimal("0.00"),
        Decimal("0.00"),
    )
    reversal = StockLedgerEntry.objects.get(txn_type=TxnType.DELETE_REVERSAL)
    assert reversal.reversal_of == posted.entries[0]


def test_rebuild_detects_and_fixes_drift(masterdata):
    post_event(
        txn_type=TxnType.ADJUSTMENT,
        source_module="tests",
        source_id=4,
        movements=[
            Movement(
                product=masterdata.phone,
                location=masterdata.sydney,
                bucket=Bucket.PHYSICAL,
                qty_in=Decimal("10"),
                aed_value=Decimal("100.00"),
            )
        ],
    )
    assert rebuild_stock_balances() == []

    # Corrupt the balance behind the ledger's back; rebuild must repair it.
    StockBalance.objects.all().update(quantity=Decimal("99"))
    drift = rebuild_stock_balances()
    assert len(drift) == 1
    assert balance(masterdata.phone, masterdata.sydney, Bucket.PHYSICAL) == (
        Decimal("10.00"),
        Decimal("100.00"),
    )
