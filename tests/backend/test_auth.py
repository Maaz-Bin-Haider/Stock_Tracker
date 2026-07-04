from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.audits.models import AuditLog
from conftest import PASSWORD


def test_login_returns_user_with_role(make_user):
    make_user(User.Role.PURCHASE, username="buyer")
    client = APIClient()

    response = client.post(
        "/api/v1/auth/login/", {"username": "buyer", "password": PASSWORD}, format="json"
    )

    assert response.status_code == 200
    assert response.json()["role"] == "PURCHASE"
    assert AuditLog.objects.filter(action=AuditLog.Action.LOGIN, user__username="buyer").exists()


def test_failed_login_is_rejected_and_audited(make_user):
    make_user(User.Role.SALE, username="seller")
    client = APIClient()

    response = client.post(
        "/api/v1/auth/login/", {"username": "seller", "password": "wrong"}, format="json"
    )

    assert response.status_code == 400
    assert AuditLog.objects.filter(
        action=AuditLog.Action.LOGIN_FAILED, record_repr="seller"
    ).exists()


def test_me_requires_authentication(db):
    assert APIClient().get("/api/v1/auth/me/").status_code in (401, 403)


def test_me_and_logout_flow(auth_client):
    client = auth_client(User.Role.VIEWER)

    me = client.get("/api/v1/auth/me/")
    assert me.status_code == 200
    assert me.json()["role"] == "VIEWER"

    assert client.post("/api/v1/auth/logout/").status_code == 204
    assert client.get("/api/v1/auth/me/").status_code in (401, 403)
    assert AuditLog.objects.filter(action=AuditLog.Action.LOGOUT).exists()


def test_disabled_user_cannot_login(make_user):
    user = make_user(User.Role.VIEWER, username="ghost")
    user.is_active = False
    user.save()

    response = APIClient().post(
        "/api/v1/auth/login/", {"username": "ghost", "password": PASSWORD}, format="json"
    )

    assert response.status_code == 400
