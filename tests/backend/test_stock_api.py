"""Read-only stock ledger/balances API tests, incl. admin-only valuation data
(FR-116 enforced server-side)."""

from decimal import Decimal

import pytest

from apps.accounts.models import User
from apps.inventory.models import Bucket, TxnType
from apps.inventory.services import Movement, post_event

pytestmark = pytest.mark.django_db

LEDGER = "/api/v1/stock/ledger/"
BALANCES = "/api/v1/stock/balances/"


@pytest.fixture
def stocked(masterdata):
    post_event(
        txn_type=TxnType.ADJUSTMENT,
        source_module="tests",
        source_id=1,
        movements=[
            Movement(
                product=masterdata.phone,
                location=masterdata.dubai,
                bucket=Bucket.PHYSICAL,
                qty_in=Decimal("10"),
                aed_value=Decimal("100.00"),
            )
        ],
    )
    return masterdata


@pytest.mark.parametrize(
    "role", [User.Role.ADMIN, User.Role.PURCHASE, User.Role.SALE, User.Role.VIEWER]
)
def test_every_role_reads_ledger_and_balances(auth_client, stocked, role):
    client = auth_client(role)
    response = client.get(LEDGER)
    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["net_qty"] == "10.00"
    assert client.get(BALANCES).status_code == 200


def test_ledger_is_read_only(auth_client, stocked):
    client = auth_client(User.Role.ADMIN)
    assert client.post(LEDGER, {}, format="json").status_code == 405
    entry_id = client.get(LEDGER).data["results"][0]["id"]
    assert client.delete(f"{LEDGER}{entry_id}/").status_code == 405


def test_balance_value_admin_only(auth_client, stocked):
    admin_row = auth_client(User.Role.ADMIN).get(BALANCES).data["results"][0]
    assert admin_row["value_aed"] == "100.00"
    for role in (User.Role.PURCHASE, User.Role.SALE, User.Role.VIEWER):
        row = auth_client(role).get(BALANCES).data["results"][0]
        assert "value_aed" not in row


def test_unauthenticated_rejected(client, stocked):
    from rest_framework.test import APIClient

    response = APIClient().get(LEDGER)
    assert response.status_code in (401, 403)
