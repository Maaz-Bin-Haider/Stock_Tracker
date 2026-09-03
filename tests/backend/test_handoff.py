"""Workspace handoff from the ERP: identity only, single-use, fail-closed."""

import base64
import hmac
import json
import time
from hashlib import sha256

import pytest
from django.core.cache import cache
from django.test import Client

from apps.accounts.models import User
from apps.audits.models import AuditLog

SECRET = "test-handoff-secret-not-for-production"
HANDOFF_URL = "/api/v1/auth/handoff/"


def make_token(username, secret=SECRET, issued_at=None, nonce=None):
    """Mirror of the ERP signer (``home/views.py::_sign_handoff``).

    Written out independently of the verifier on purpose: if either side's wire
    format drifts, these tests fail instead of production silently rejecting
    every handoff.
    """
    payload = json.dumps(
        {
            "u": username,
            "t": int(time.time() if issued_at is None else issued_at),
            "n": nonce or f"nonce-{time.time_ns()}",
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    body = base64.urlsafe_b64encode(payload).rstrip(b"=").decode()
    signature = (
        base64.urlsafe_b64encode(hmac.new(secret.encode(), body.encode(), sha256).digest())
        .rstrip(b"=")
        .decode()
    )
    return f"{body}.{signature}"


@pytest.fixture(autouse=True)
def handoff_enabled(settings):
    settings.WORKSPACE_HANDOFF_SECRET = SECRET
    settings.WORKSPACE_HANDOFF_MAX_AGE_SECONDS = 30
    cache.clear()
    yield
    cache.clear()


def test_valid_token_opens_a_session(make_user):
    make_user(User.Role.SALE, username="ahmed")

    response = Client().get(HANDOFF_URL, {"t": make_token("ahmed")})

    assert response.status_code == 302
    assert response["Location"] == "/"
    assert AuditLog.objects.filter(
        action=AuditLog.Action.LOGIN, module="auth.handoff", user__username="ahmed"
    ).exists()


def test_handed_off_session_is_usable_and_keeps_its_own_role(make_user):
    make_user(User.Role.VIEWER, username="ahmed")
    client = Client()

    client.get(HANDOFF_URL, {"t": make_token("ahmed")})

    me = client.get("/api/v1/auth/me/")
    assert me.status_code == 200
    # The token asserted identity only; the role is this system's alone.
    assert me.json()["role"] == "VIEWER"


def test_token_is_single_use(make_user):
    make_user(User.Role.SALE, username="ahmed")
    token = make_token("ahmed")

    assert Client().get(HANDOFF_URL, {"t": token})["Location"] == "/"
    replay = Client().get(HANDOFF_URL, {"t": token})

    assert replay["Location"] == "/login"
    assert AuditLog.objects.filter(
        action=AuditLog.Action.LOGIN_FAILED, module="auth.handoff"
    ).exists()


@pytest.mark.parametrize(
    "token_factory, label",
    [
        (lambda: make_token("ahmed", secret="a-different-secret"), "wrong secret"),
        (lambda: make_token("ahmed")[:-4] + "AAAA", "tampered signature"),
        (lambda: make_token("ahmed").split(".")[0], "unsigned"),
        (lambda: make_token("ahmed", issued_at=time.time() - 3600), "expired"),
        (lambda: make_token("ahmed", issued_at=time.time() + 3600), "future-dated"),
        (lambda: "not-a-token", "malformed"),
        (lambda: "", "absent"),
    ],
)
def test_unusable_tokens_are_refused(make_user, token_factory, label):
    make_user(User.Role.SALE, username="ahmed")

    response = Client().get(HANDOFF_URL, {"t": token_factory()})

    assert response["Location"] == "/login", label
    assert "_auth_user_id" not in Client().session


def test_unknown_username_never_creates_an_account(db):
    response = Client().get(HANDOFF_URL, {"t": make_token("nobody")})

    assert response["Location"] == "/login"
    assert not User.objects.filter(username="nobody").exists()


def test_disabled_account_is_refused(make_user):
    user = make_user(User.Role.SALE, username="ghost")
    user.is_active = False
    user.save()

    assert Client().get(HANDOFF_URL, {"t": make_token("ghost")})["Location"] == "/login"


def test_endpoint_is_inert_without_a_configured_secret(make_user, settings):
    make_user(User.Role.SALE, username="ahmed")
    token = make_token("ahmed")
    settings.WORKSPACE_HANDOFF_SECRET = ""

    response = Client().get(HANDOFF_URL, {"t": token})

    assert response["Location"] == "/login"
    assert not AuditLog.objects.filter(action=AuditLog.Action.LOGIN).exists()


def test_handoff_rejects_non_get(make_user):
    make_user(User.Role.SALE, username="ahmed")

    assert Client().post(HANDOFF_URL, {"t": make_token("ahmed")}).status_code == 405


def test_direct_password_login_still_works(make_user):
    """The handoff must not disturb the standalone login path."""
    from conftest import PASSWORD

    make_user(User.Role.SALE, username="ahmed")

    response = Client().post(
        "/api/v1/auth/login/",
        json.dumps({"username": "ahmed", "password": PASSWORD}),
        content_type="application/json",
    )

    assert response.status_code == 200
