"""Workspace handoff: open a Stock Tracker session from an ERP-signed token.

The ERP and this system stay independent — separate databases, separate roles,
separate sessions. A handoff token asserts *identity only*: which employee is
arriving. What that employee may do here is decided, exactly as before, by
their Stock Tracker role through ``ROLE_MATRIX``. No role, permission or
group ever crosses the boundary.

Deliberate properties:

* **No account is ever created.** An unknown, disabled or unmatched username
  falls through to the normal login page.
* **Tokens are single-use and short-lived.** HMAC-SHA256 over the payload with
  a secret shared only through the environment, valid for
  ``WORKSPACE_HANDOFF_MAX_AGE_SECONDS``, and the nonce is burned in the shared
  cache on first arrival so a token in a browser history or proxy log cannot be
  replayed.
* **Inert until switched on.** With no secret configured the endpoint always
  redirects to the login page, so deploying this code changes nothing until an
  operator sets the same secret in both systems.
* **Direct login is untouched.** Nothing here alters the username/password
  flow; the Stock Tracker still works standalone.

Trust boundary — read before changing anything here. Whoever can mint tokens
(anyone holding the secret, or anyone who has compromised the ERP) can open a
session here as any existing active user. That is inherent to a handoff of this
shape. It is why the secret lives only in the environment, is never reused for
anything else, and why every rejection is audited.
"""

import base64
import binascii
import hmac
import json
import time
from hashlib import sha256

from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.core.cache import cache
from django.http import HttpResponseRedirect
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from apps.audits.models import AuditLog
from apps.audits.services import record_audit

# Fixed destinations: never redirect anywhere derived from the request, so a
# handoff URL can never be turned into an open redirect.
LOGIN_PATH = "/login"
HOME_PATH = "/"

MAX_TOKEN_CHARS = 512
NONCE_CACHE_PREFIX = "workspace-handoff:"
AUDIT_MODULE = "auth.handoff"


class HandoffError(Exception):
    """Token absent, malformed, unsigned, stale, replayed or unusable."""


def _b64decode(value):
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def verify_token(token, secret):
    """Return the asserted username, or raise ``HandoffError``.

    The reason in the exception is for the audit trail only — it is never shown
    to the caller, who always gets the same redirect whatever went wrong.
    """
    if not token or len(token) > MAX_TOKEN_CHARS:
        raise HandoffError("missing or oversized token")

    body, separator, signature = token.partition(".")
    if not body or not separator or not signature:
        raise HandoffError("malformed token")

    try:
        provided = _b64decode(signature)
    except (binascii.Error, ValueError) as exc:
        raise HandoffError("unreadable signature") from exc

    expected = hmac.new(secret.encode(), body.encode(), sha256).digest()
    if not hmac.compare_digest(expected, provided):
        raise HandoffError("bad signature")

    try:
        payload = json.loads(_b64decode(body))
    except (binascii.Error, ValueError, UnicodeDecodeError) as exc:
        raise HandoffError("unreadable payload") from exc
    if not isinstance(payload, dict):
        raise HandoffError("unreadable payload")

    username = payload.get("u")
    issued_at = payload.get("t")
    nonce = payload.get("n")
    if not isinstance(username, str) or not username:
        raise HandoffError("no username")
    if isinstance(issued_at, bool) or not isinstance(issued_at, int):
        raise HandoffError("no issue time")
    if not isinstance(nonce, str) or not nonce:
        raise HandoffError("no nonce")

    max_age = settings.WORKSPACE_HANDOFF_MAX_AGE_SECONDS
    age = time.time() - issued_at
    # Reject future-dated tokens as firmly as expired ones: a clock skewed
    # forward must not widen the window.
    if not -max_age <= age <= max_age:
        raise HandoffError("expired or future-dated token")

    # cache.add() is atomic, so the first arrival burns the nonce and every
    # replay loses. Held well past the token's own lifetime.
    if not cache.add(f"{NONCE_CACHE_PREFIX}{nonce}", 1, timeout=max_age * 4):
        raise HandoffError("replayed token")

    return username


@never_cache
@require_GET
def workspace_handoff(request):
    """Consume an ERP handoff token and start this system's own session."""
    secret = settings.WORKSPACE_HANDOFF_SECRET
    if not secret:
        return HttpResponseRedirect(LOGIN_PATH)

    def reject(reason):
        record_audit(
            action=AuditLog.Action.LOGIN_FAILED,
            module=AUDIT_MODULE,
            record_repr=reason[:255],
            user=None,
        )
        return HttpResponseRedirect(LOGIN_PATH)

    try:
        username = verify_token(request.GET.get("t", ""), secret)
    except HandoffError as exc:
        return reject(f"rejected: {exc}")

    user = get_user_model().objects.filter(username=username, is_active=True).first()
    if user is None:
        # The employee has no usable account here. Onboarding stays a
        # deliberate admin action in this system; a handoff never creates one.
        return reject(f"no active account for {username}")

    # Explicit backend: the user came from a query, not authenticate().
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    record_audit(action=AuditLog.Action.LOGIN, module=AUDIT_MODULE, user=user)
    return HttpResponseRedirect(HOME_PATH)
