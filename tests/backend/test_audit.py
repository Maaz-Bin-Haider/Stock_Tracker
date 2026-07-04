"""Master data CRUD auditing with before/after snapshots — M1 exit criterion."""

from apps.audits.models import AuditLog


def test_create_update_delete_are_audited_with_snapshots(admin_client):
    created = admin_client.post(
        "/api/v1/categories/", {"name": "Tablets"}, format="json"
    ).json()

    create_log = AuditLog.objects.get(action=AuditLog.Action.CREATE, module="categories")
    assert create_log.record_id == created["id"]
    assert create_log.after_values["name"] == "Tablets"
    assert create_log.user.username == "admin_user"

    admin_client.patch(f"/api/v1/categories/{created['id']}/", {"name": "iPads"}, format="json")

    update_log = AuditLog.objects.get(action=AuditLog.Action.UPDATE, module="categories")
    assert update_log.before_values["name"] == "Tablets"
    assert update_log.after_values["name"] == "iPads"

    admin_client.delete(f"/api/v1/categories/{created['id']}/")

    delete_log = AuditLog.objects.get(action=AuditLog.Action.DELETE, module="categories")
    assert delete_log.before_values["name"] == "iPads"


def test_audit_log_is_visible_to_all_roles_and_read_only(auth_client):
    viewer = auth_client("VIEWER")

    assert viewer.get("/api/v1/audit/").status_code == 200
    assert viewer.post("/api/v1/audit/", {}, format="json").status_code == 405


def test_audit_rows_capture_request_context(admin_client):
    admin_client.post("/api/v1/categories/", {"name": "Ctx"}, format="json")

    log = AuditLog.objects.get(action=AuditLog.Action.CREATE, module="categories")
    assert log.ip_address is not None
    assert log.session_key != ""
