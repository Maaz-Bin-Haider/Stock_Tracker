"""Product master rules: FR-018 (case-insensitive duplicates) and FR-019 (variants)."""

import pytest

from apps.masterdata.models import Category
from apps.products.models import Product


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


def test_large_product_catalog_is_available_across_all_api_pages(admin_client, category):
    Product.objects.bulk_create(
        [
            Product(name=f"Product {number:03d}", category=category, storage_specs="Standard")
            for number in range(1, 206)
        ]
    )

    first_page = admin_client.get("/api/v1/products/?is_active=true")
    final_page = admin_client.get("/api/v1/products/?is_active=true&page=5")

    assert first_page.status_code == 200
    assert first_page.data["count"] == 205
    assert len(first_page.data["results"]) == 50
    assert first_page.data["next"].endswith("?is_active=true&page=2")
    assert final_page.status_code == 200
    assert [row["name"] for row in final_page.data["results"]] == [
        "Product 201",
        "Product 202",
        "Product 203",
        "Product 204",
        "Product 205",
    ]
