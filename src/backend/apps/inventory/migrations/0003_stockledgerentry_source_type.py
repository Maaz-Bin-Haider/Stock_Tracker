"""Add StockLedgerEntry.source_type and backfill it for existing rows.

``(source_module, source_id)`` never addressed one record: the purchases module
owns purchases, collections and refunds, so "purchases#3" matches three
different rows that all exist. ``txn_type`` covered most cases but not the
reversals — deleting a purchase, a collection or a refund all post
DELETE_REVERSAL in the same module.

The backfill is deterministic, not a guess:

* Every txn_type except the two reversals names exactly one record type.
* EDIT_REVERSAL is posted only by purchases, sales and stock adjustments, one
  record type each.
* DELETE_REVERSAL is resolved by how the reversal was built. Deleting a
  purchase posts movements computed from remainders, so ``reversal_of`` is
  NULL; deleting a collection or a refund reverses that record's own rows, so
  ``reversal_of`` points at a PURCHASE_COLLECTION / PURCHASE_REFUND row.
  Deleting a shipment reverses every row its lines ever posted, so the group
  includes a reversal of a SHIPMENT_OUT row; deleting a receipt reverses only
  SHIPMENT_RECEIPT rows.

The migration refuses to complete if any row is left unresolved, so a silent
wrong value can never reach the source of truth.
"""

from django.db import migrations, models

# Straightforward one-to-one mappings.
BY_TXN_TYPE = {
    "PURCHASE_ENTRY": "PURCHASE",
    "PURCHASE_COLLECTION": "PURCHASE_COLLECTION",
    "PURCHASE_REFUND": "PURCHASE_REFUND",
    "SHIPMENT_OUT": "SHIPMENT",
    "SHIPMENT_CANCEL": "SHIPMENT",
    "SHIPMENT_RECEIPT": "SHIPMENT_RECEIPT",
    "SALE": "SALE",
    "ADJUSTMENT": "STOCK_ADJUSTMENT",
}

# EDIT_REVERSAL is unambiguous per module: only one record type in each module
# is editable in a way that reposts stock.
EDIT_REVERSAL_BY_MODULE = {
    "purchases": "PURCHASE",
    "sales": "SALE",
    "stock_adjustments": "STOCK_ADJUSTMENT",
}

DELETE_REVERSAL_BY_MODULE = {
    "sales": "SALE",
    "stock_adjustments": "STOCK_ADJUSTMENT",
}


def _resolve_purchase_delete(entry, reversed_txn_types):
    """A purchase delete carries no reversal_of; a collection/refund delete does."""
    origin = reversed_txn_types.get(entry.reversal_of_id)
    if origin == "PURCHASE_COLLECTION":
        return "PURCHASE_COLLECTION"
    if origin == "PURCHASE_REFUND":
        return "PURCHASE_REFUND"
    if origin is None:
        return "PURCHASE"
    # Reversing a PURCHASE_ENTRY row can only come from the purchase itself.
    return "PURCHASE"


def backfill(apps, schema_editor):
    StockLedgerEntry = apps.get_model("inventory", "StockLedgerEntry")

    entries = list(StockLedgerEntry.objects.all())
    if not entries:
        return

    # txn_type of every row that is the target of a reversal, for origin lookups.
    reversed_txn_types = {
        row["id"]: row["txn_type"]
        for row in StockLedgerEntry.objects.filter(
            id__in=[e.reversal_of_id for e in entries if e.reversal_of_id]
        ).values("id", "txn_type")
    }

    # A shipment delete reverses the whole shipment, so its group contains a
    # reversal of a SHIPMENT_OUT row; a receipt delete never does.
    shipment_delete_groups = set()
    for entry in entries:
        if (
            entry.txn_type == "DELETE_REVERSAL"
            and entry.source_module == "shipments"
            and reversed_txn_types.get(entry.reversal_of_id) == "SHIPMENT_OUT"
        ):
            shipment_delete_groups.add(entry.source_id)

    updated = []
    unresolved = []
    for entry in entries:
        source_type = BY_TXN_TYPE.get(entry.txn_type)
        if source_type is None and entry.txn_type == "EDIT_REVERSAL":
            source_type = EDIT_REVERSAL_BY_MODULE.get(entry.source_module)
        if source_type is None and entry.txn_type == "DELETE_REVERSAL":
            if entry.source_module == "purchases":
                source_type = _resolve_purchase_delete(entry, reversed_txn_types)
            elif entry.source_module == "shipments":
                source_type = (
                    "SHIPMENT"
                    if entry.source_id in shipment_delete_groups
                    else "SHIPMENT_RECEIPT"
                )
            else:
                source_type = DELETE_REVERSAL_BY_MODULE.get(entry.source_module)

        if not source_type:
            unresolved.append((entry.id, entry.source_module, entry.txn_type))
            continue
        entry.source_type = source_type
        updated.append(entry)

    if unresolved:
        raise RuntimeError(
            "Cannot determine source_type for ledger rows "
            f"(id, module, txn_type): {unresolved[:20]}"
        )

    StockLedgerEntry.objects.bulk_update(updated, ["source_type"], batch_size=500)


def unbackfill(apps, schema_editor):
    """Nothing to undo — the column is dropped by the reverse schema step."""


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0002_stockadjustment"),
    ]

    operations = [
        migrations.AddField(
            model_name="stockledgerentry",
            name="source_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("PURCHASE", "Purchase invoice"),
                    ("PURCHASE_COLLECTION", "Purchase collection"),
                    ("PURCHASE_REFUND", "Purchase refund/cancellation"),
                    ("SHIPMENT", "Shipment"),
                    ("SHIPMENT_RECEIPT", "Shipment receipt"),
                    ("SALE", "Sale"),
                    ("STOCK_ADJUSTMENT", "Stock adjustment"),
                ],
                default="",
                max_length=32,
            ),
        ),
        migrations.RunPython(backfill, unbackfill),
        # Only now that every row carries a value: drop the placeholder default
        # so new rows must supply one.
        migrations.AlterField(
            model_name="stockledgerentry",
            name="source_type",
            field=models.CharField(
                choices=[
                    ("PURCHASE", "Purchase invoice"),
                    ("PURCHASE_COLLECTION", "Purchase collection"),
                    ("PURCHASE_REFUND", "Purchase refund/cancellation"),
                    ("SHIPMENT", "Shipment"),
                    ("SHIPMENT_RECEIPT", "Shipment receipt"),
                    ("SALE", "Sale"),
                    ("STOCK_ADJUSTMENT", "Stock adjustment"),
                ],
                max_length=32,
            ),
        ),
        migrations.AddIndex(
            model_name="stockledgerentry",
            index=models.Index(
                fields=["source_type", "source_id"], name="inventory_s_source__6d7e0a_idx"
            ),
        ),
    ]
