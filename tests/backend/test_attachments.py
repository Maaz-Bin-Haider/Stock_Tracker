"""Invoice/bill upload tests (FR-035/FR-073/FR-104…FR-107): images + PDF only
with content sniffing, module-scoped write permissions, audited uploads, and
the Upload/File report."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.models import User
from apps.attachments.models import FileAttachment
from apps.audits.models import AuditLog

pytestmark = pytest.mark.django_db

ATTACHMENTS = "/api/v1/attachments/"

PDF_BYTES = b"%PDF-1.4 fake little invoice"
PNG_BYTES = b"\x89PNG\r\n\x1a\n rest-of-image"


@pytest.fixture
def business_records(auth_client, masterdata):
    """One purchase and one sale to attach files to."""
    purchase_client = auth_client(User.Role.PURCHASE)
    sale_client = auth_client(User.Role.SALE)

    purchase = purchase_client.post(
        "/api/v1/purchases/",
        {
            "invoice_no": "INV-ATT",
            "purchase_date": "2026-07-01",
            "location": masterdata.dubai.pk,
            "supplier": masterdata.supplier.pk,
            "lines": [
                {
                    "product": masterdata.phone.pk,
                    "quantity": "5",
                    "unit_price": "100.00",
                    "currency": masterdata.aed.pk,
                    "collected_qty": "5",
                }
            ],
        },
        format="json",
    )
    assert purchase.status_code == 201, purchase.data

    from apps.masterdata.models import Customer

    customer = Customer.objects.create(name="Attachment Customer")
    sale = sale_client.post(
        "/api/v1/sales/",
        {
            "sale_date": "2026-07-02",
            "location": masterdata.dubai.pk,
            "customer": customer.pk,
            "lines": [{"product": masterdata.phone.pk, "quantity": "1"}],
        },
        format="json",
    )
    assert sale.status_code == 201, sale.data

    class Records:
        pass

    records = Records()
    records.purchase_id = purchase.data["id"]
    records.sale_id = sale.data["id"]
    records.purchase_client = purchase_client
    records.sale_client = sale_client
    return records


def upload(client, module, record_id, *, name="invoice.pdf", content=PDF_BYTES):
    return client.post(
        ATTACHMENTS,
        {
            "module": module,
            "record_id": record_id,
            "file": SimpleUploadedFile(name, content),
        },
        format="multipart",
    )


class TestUpload:
    def test_purchase_user_uploads_pdf(self, business_records):
        response = upload(
            business_records.purchase_client, "purchases", business_records.purchase_id
        )
        assert response.status_code == 201, response.data
        assert response.data["original_name"] == "invoice.pdf"
        assert response.data["content_type"] == "application/pdf"
        assert response.data["download_url"].endswith("/download/")
        # FR-107: the upload is audited.
        assert AuditLog.objects.filter(module="attachments", action="CREATE").exists()

    def test_sale_user_uploads_image_to_sale(self, business_records):
        response = upload(
            business_records.sale_client,
            "sales",
            business_records.sale_id,
            name="receipt.png",
            content=PNG_BYTES,
        )
        assert response.status_code == 201, response.data
        assert response.data["content_type"] == "image/png"

    def test_download_roundtrip(self, business_records, auth_client):
        created = upload(
            business_records.purchase_client, "purchases", business_records.purchase_id
        ).data
        viewer = auth_client(User.Role.VIEWER)  # FR-106: all users can download
        response = viewer.get(f"{ATTACHMENTS}{created['id']}/download/")
        assert response.status_code == 200
        assert b"".join(response.streaming_content) == PDF_BYTES

    def test_list_filter_by_record(self, business_records):
        upload(business_records.purchase_client, "purchases", business_records.purchase_id)
        upload(business_records.sale_client, "sales", business_records.sale_id)
        response = business_records.purchase_client.get(
            ATTACHMENTS,
            {"module": "purchases", "record_id": business_records.purchase_id},
        )
        assert response.data["count"] == 1
        assert response.data["results"][0]["module"] == "purchases"


class TestUploadValidation:
    def test_content_sniffing_rejects_renamed_file(self, business_records):
        response = upload(
            business_records.purchase_client,
            "purchases",
            business_records.purchase_id,
            name="malware.pdf",
            content=b"MZ\x90\x00 definitely not a pdf",
        )
        assert response.status_code == 400
        assert not FileAttachment.objects.exists()

    def test_size_cap(self, business_records, monkeypatch):
        from apps.attachments import serializers

        monkeypatch.setattr(serializers, "MAX_SIZE", 10)
        response = upload(
            business_records.purchase_client, "purchases", business_records.purchase_id
        )
        assert response.status_code == 400
        assert "10" in str(response.data)

    def test_unknown_module_rejected(self, business_records):
        response = upload(business_records.purchase_client, "shipments", 1)
        assert response.status_code == 400

    def test_missing_record_rejected(self, business_records):
        response = upload(business_records.purchase_client, "purchases", 99999)
        assert response.status_code == 400


class TestUploadPermissions:
    def test_sale_user_cannot_upload_to_purchases(self, business_records):
        response = upload(
            business_records.sale_client, "purchases", business_records.purchase_id
        )
        assert response.status_code == 403

    def test_viewer_cannot_upload(self, business_records, auth_client):
        response = upload(
            auth_client(User.Role.VIEWER), "purchases", business_records.purchase_id
        )
        assert response.status_code == 403

    def test_delete_follows_module_role(self, business_records):
        created = upload(
            business_records.purchase_client, "purchases", business_records.purchase_id
        ).data
        denied = business_records.sale_client.delete(f"{ATTACHMENTS}{created['id']}/")
        assert denied.status_code == 403
        allowed = business_records.purchase_client.delete(f"{ATTACHMENTS}{created['id']}/")
        assert allowed.status_code == 204
        assert not FileAttachment.objects.filter(pk=created["id"]).exists()
        assert AuditLog.objects.filter(module="attachments", action="DELETE").exists()


class TestUploadReport:
    def test_uploads_report_lists_files(self, business_records, auth_client):
        upload(business_records.purchase_client, "purchases", business_records.purchase_id)
        admin = auth_client(User.Role.ADMIN)
        response = admin.get("/api/v1/reports/uploads/")
        assert response.status_code == 200
        rows = response.data["sections"][0]["rows"]
        assert len(rows) == 1
        assert rows[0]["original_name"] == "invoice.pdf"
        assert rows[0]["record"] == f"purchases#{business_records.purchase_id}"
        assert rows[0]["download_url"].endswith("/download/")


class TestThemePreference:
    def test_theme_saved_on_profile(self, auth_client):
        client = auth_client(User.Role.VIEWER)
        response = client.patch("/api/v1/auth/me/", {"theme": "DARK"}, format="json")
        assert response.status_code == 200, response.data
        assert response.data["theme"] == "DARK"
        assert client.get("/api/v1/auth/me/").data["theme"] == "DARK"

    def test_invalid_theme_rejected(self, auth_client):
        client = auth_client(User.Role.VIEWER)
        response = client.patch("/api/v1/auth/me/", {"theme": "NEON"}, format="json")
        assert response.status_code == 400

    def test_role_not_editable_via_me(self, auth_client):
        client = auth_client(User.Role.VIEWER)
        response = client.patch("/api/v1/auth/me/", {"role": "ADMIN"}, format="json")
        assert response.status_code == 200
        assert response.data["role"] == "VIEWER"
