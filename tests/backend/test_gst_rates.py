"""GST rate management and how purchase entry resolves a rate.

Written after a production incident: a GST rate was given an end date, every
attempt to remove it saved successfully while changing nothing, and once that
date passed, purchase entry at those locations would have been refused with no
way to fix it from the UI.
"""

import datetime
from decimal import Decimal

import pytest

from apps.accounts.models import User
from apps.masterdata.models import GstRate

pytestmark = pytest.mark.django_db


@pytest.fixture
def gst_rate(masterdata):
    """Sydney's open-ended 10% rate, then given an end date."""
    rate = GstRate.objects.get(location=masterdata.sydney)
    rate.effective_to = datetime.date(2026, 9, 7)
    rate.save(update_fields=["effective_to"])
    return rate


def test_an_end_date_can_be_cleared_through_the_api(admin_client, gst_rate):
    """The fix depends on the API accepting null here, so pin that contract."""
    response = admin_client.patch(
        f"/api/v1/gst-rates/{gst_rate.pk}/", {"effective_to": None}, format="json"
    )

    assert response.status_code == 200, response.data
    assert response.data["effective_to"] is None
    gst_rate.refresh_from_db()
    assert gst_rate.effective_to is None


def test_omitting_the_end_date_leaves_it_alone(admin_client, gst_rate):
    """The other half of the contract, and the reason the form had to send an
    explicit null: a PATCH without the key means "unchanged", so a form that
    dropped cleared fields could never remove a date once set."""
    response = admin_client.patch(
        f"/api/v1/gst-rates/{gst_rate.pk}/", {"rate": "10.00"}, format="json"
    )

    assert response.status_code == 200, response.data
    assert response.data["effective_to"] == "2026-09-07"


def _purchase(client, world, purchase_date):
    return client.post(
        "/api/v1/purchases/",
        {
            "invoice_no": f"INV-{purchase_date}",
            "purchase_date": str(purchase_date),
            "location": world.sydney.pk,
            "supplier": world.supplier.pk,
            "lines": [
                {
                    "product": world.phone.pk,
                    "quantity": "1",
                    "unit_price": "100.00",
                    "currency": world.aud.pk,
                }
            ],
        },
        format="json",
    )


def test_a_rate_applies_up_to_and_including_its_end_date(masterdata, auth_client, gst_rate):
    client = auth_client(User.Role.PURCHASE)

    response = _purchase(client, masterdata, datetime.date(2026, 9, 7))

    assert response.status_code == 201, response.data
    assert Decimal(response.data["lines"][0]["gst_rate_percent"]) == Decimal("10.00")


def test_an_expired_rate_with_no_successor_blocks_purchase_entry(
    masterdata, auth_client, gst_rate
):
    """The production failure mode. It is a deliberate refusal rather than a
    silent 0% — a GST region quietly recording no GST would be worse — but it
    leaves the location unusable until someone adds a rate."""
    client = auth_client(User.Role.PURCHASE)

    response = _purchase(client, masterdata, datetime.date(2026, 9, 8))

    assert response.status_code == 400
    assert "no active GST rate" in str(response.data)


def test_a_successor_rate_takes_over_the_day_after_the_previous_one_ends(
    masterdata, auth_client, gst_rate
):
    GstRate.objects.create(
        location=masterdata.sydney,
        rate=Decimal("12.50"),
        effective_from=datetime.date(2026, 9, 8),
    )
    client = auth_client(User.Role.PURCHASE)

    on_end_date = _purchase(client, masterdata, datetime.date(2026, 9, 7))
    day_after = _purchase(client, masterdata, datetime.date(2026, 9, 8))

    assert Decimal(on_end_date.data["lines"][0]["gst_rate_percent"]) == Decimal("10.00")
    assert Decimal(day_after.data["lines"][0]["gst_rate_percent"]) == Decimal("12.50")


def test_the_newest_rate_effective_on_the_date_wins(masterdata, auth_client):
    """Overlapping open-ended rows are the shape an operator creates by adding a
    new rate without closing the old one."""
    GstRate.objects.create(
        location=masterdata.sydney,
        rate=Decimal("11.00"),
        effective_from=datetime.date(2026, 6, 1),
    )
    client = auth_client(User.Role.PURCHASE)

    before = _purchase(client, masterdata, datetime.date(2026, 5, 31))
    after = _purchase(client, masterdata, datetime.date(2026, 6, 1))

    assert Decimal(before.data["lines"][0]["gst_rate_percent"]) == Decimal("10.00")
    assert Decimal(after.data["lines"][0]["gst_rate_percent"]) == Decimal("11.00")


def test_an_inactive_rate_is_ignored(masterdata, auth_client, gst_rate):
    gst_rate.effective_to = None
    gst_rate.is_active = False
    gst_rate.save(update_fields=["effective_to", "is_active"])
    client = auth_client(User.Role.PURCHASE)

    response = _purchase(client, masterdata, datetime.date(2026, 9, 7))

    assert response.status_code == 400
    assert "no active GST rate" in str(response.data)


def test_an_explicit_rate_on_the_line_overrides_settings(masterdata, auth_client, gst_rate):
    """FR-089: a manual override wins, including when Settings would refuse."""
    client = auth_client(User.Role.PURCHASE)

    response = client.post(
        "/api/v1/purchases/",
        {
            "invoice_no": "INV-OVERRIDE",
            "purchase_date": "2026-09-08",
            "location": masterdata.sydney.pk,
            "supplier": masterdata.supplier.pk,
            "lines": [
                {
                    "product": masterdata.phone.pk,
                    "quantity": "2",
                    "unit_price": "100.00",
                    "currency": masterdata.aud.pk,
                    "gst_rate_percent": "7.50",
                }
            ],
        },
        format="json",
    )

    assert response.status_code == 201, response.data
    line = response.data["lines"][0]
    assert Decimal(line["gst_rate_percent"]) == Decimal("7.50")
    # 2 x 100 AUD at 7.5% = 15 AUD, x 2.4 = 36 AED.
    assert Decimal(line["gst_amount"]) == Decimal("15.00")
    assert Decimal(line["gst_amount_aed"]) == Decimal("36.00")


def test_a_non_gst_location_records_no_gst(masterdata, auth_client):
    client = auth_client(User.Role.PURCHASE)

    response = client.post(
        "/api/v1/purchases/",
        {
            "invoice_no": "INV-DUBAI",
            "purchase_date": "2026-09-07",
            "location": masterdata.dubai.pk,
            "supplier": masterdata.supplier.pk,
            "lines": [
                {
                    "product": masterdata.phone.pk,
                    "quantity": "3",
                    "unit_price": "50.00",
                    "currency": masterdata.aed.pk,
                }
            ],
        },
        format="json",
    )

    assert response.status_code == 201, response.data
    line = response.data["lines"][0]
    assert Decimal(line["gst_rate_percent"]) == Decimal("0.00")
    assert Decimal(line["gst_amount"]) == Decimal("0.00")
