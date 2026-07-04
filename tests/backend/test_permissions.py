"""Role matrix enforcement per SYSTEM_SPEC §6 — the M1 exit criterion."""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.masterdata.models import Category

ROLES = [User.Role.ADMIN, User.Role.PURCHASE, User.Role.SALE, User.Role.VIEWER]

# endpoint, create payload, roles allowed to write
WRITE_CASES = [
    ("/api/v1/categories/", {"name": "Drones"}, {"ADMIN", "PURCHASE", "SALE"}),
    ("/api/v1/locations/", {"name": "Lahore"}, {"ADMIN"}),
    ("/api/v1/currencies/", {"code": "GBP"}, {"ADMIN"}),
    ("/api/v1/suppliers/", {"name": "Acme Wholesale"}, {"ADMIN", "PURCHASE"}),
    ("/api/v1/customers/", {"name": "Walk-in"}, {"ADMIN", "SALE"}),
]


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("endpoint,payload,allowed", WRITE_CASES)
def test_write_access_follows_role_matrix(auth_client, role, endpoint, payload, allowed):
    response = auth_client(role).post(endpoint, payload, format="json")

    expected = 201 if role in allowed else 403
    assert response.status_code == expected, response.content


@pytest.mark.parametrize("role", ROLES)
def test_all_roles_can_read_master_data(auth_client, role):
    client = auth_client(role)
    for endpoint in ["/api/v1/categories/", "/api/v1/locations/", "/api/v1/products/"]:
        assert client.get(endpoint).status_code == 200


@pytest.mark.parametrize("role", ROLES)
def test_products_writable_by_admin_and_purchase_only(auth_client, role):
    category = Category.objects.create(name="Phones")
    payload = {"name": "iPhone 15 Pro", "category": category.pk, "storage_specs": "256GB"}

    response = auth_client(role).post("/api/v1/products/", payload, format="json")

    expected = 201 if role in {"ADMIN", "PURCHASE"} else 403
    assert response.status_code == expected, response.content


@pytest.mark.parametrize("role", [User.Role.PURCHASE, User.Role.SALE, User.Role.VIEWER])
def test_users_endpoint_is_admin_only(auth_client, role):
    client = auth_client(role)

    assert client.get("/api/v1/users/").status_code == 403
    assert client.post("/api/v1/users/", {"username": "x"}, format="json").status_code == 403


def test_admin_can_manage_users(admin_client):
    response = admin_client.post(
        "/api/v1/users/",
        {"username": "newbie", "password": "S3curePass!", "role": "VIEWER"},
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["role"] == "VIEWER"
    assert "password" not in response.json()


def test_users_cannot_be_deleted(admin_client, make_user):
    user = make_user(User.Role.VIEWER, username="target")

    assert admin_client.delete(f"/api/v1/users/{user.pk}/").status_code == 405


def test_anonymous_requests_are_rejected(db):
    client = APIClient()

    assert client.get("/api/v1/categories/").status_code in (401, 403)
    assert client.post("/api/v1/categories/", {"name": "X"}).status_code in (401, 403)
