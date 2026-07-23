"""Offline / local production settings (Phase M9).

Runs the stack in production mode (DEBUG=False, gunicorn, Next.js production
build) on a single local machine or office LAN with NO cloud dependency and
typically NO TLS (plain HTTP over a trusted LAN).

Deliberately separate from prod.py (the AWS/TLS profile, M8): over plain HTTP a
"secure" cookie is never sent, so login would silently break. Secure cookies and
HSTS therefore default OFF here and can be re-enabled with DJANGO_SECURE_COOKIES=1
if the operator later terminates TLS in front of nginx.
"""

import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403

DEBUG = False

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY must be set for local production. Copy "
        "deployment/env.prod.example to deployment/.env.prod and set a value "
        "(generate one with: "
        "python -c 'import secrets; print(secrets.token_urlsafe(50))')."
    )

# ALLOWED_HOSTS is read from DJANGO_ALLOWED_HOSTS in base.py; set it to include the
# server's LAN IP/hostname, e.g. "localhost,127.0.0.1,backend,192.168.1.50,stock.local".

# The SPA's CSRF check trusts the exact origin(s) users type in the browser,
# scheme + host + port, e.g. "http://192.168.1.50:8080,http://stock.local:8080".
CSRF_TRUSTED_ORIGINS = [
    origin
    for origin in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin
]

# Plain HTTP on a trusted LAN by default. Set DJANGO_SECURE_COOKIES=1 only when TLS
# terminates in front of the app, otherwise cookies stop flowing and login breaks.
_secure = os.environ.get("DJANGO_SECURE_COOKIES", "0") == "1"
SESSION_COOKIE_SECURE = _secure
CSRF_COOKIE_SECURE = _secure
if _secure:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
