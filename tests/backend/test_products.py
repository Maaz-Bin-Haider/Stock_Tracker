"""Product master rules: FR-018 (case-insensitive duplicates) and FR-019 (variants)."""

import pytest

from apps.masterdata.models import Category


@pytest.fixture
def category(db):
    return Category.objects.create(name="Phones")


def _payload(category, **overrides):
    return {"name": "iPhone 12", "category": category.pk, "storage_specs": "128GB", **overrides}


def test_exact_duplicate_rejected_case_insensitively(admin_client, category):
    assert admin_client.post("/api/v1/products/", _payload(category), format="json").status_code == 201

    response = admin_client.post(
        "/api/v1/products/", _payload(category, name="IPHONE 12"), format="json"
    )

    assert response.status_code == 400
    assert "already exists" in str(response.json())


def test_same_name_with_different_specs_allowed(admin_client, category):
    assert admin_client.post("/api/v1/products/", _payload(category), format="json").status_code == 201

    response = admin_client.post(
        "/api/v1/products/", _payload(category, storage_specs="256GB"), format="json"
    )

    assert response.status_code == 201


def test_update_does_not_collide_with_itself(admin_client, category):
    created = admin_client.post("/api/v1/products/", _payload(category), format="json").json()

    response = admin_client.patch(
        f"/api/v1/products/{created['id']}/", {"brand": "Apple"}, format="json"
    )

    assert response.status_code == 200
    assert response.json()["brand"] == "Apple"
