from .base import *  # noqa: F403

DEBUG = True

# The dev proxy forwards `Host: $host`, which nginx gives without the port, so
# Django builds "http://localhost" and rejects the browser's
# "Origin: http://localhost:8080". Without these, every authenticated write from
# a browser through the dev stack fails with "CSRF Failed: Origin checking
# failed" — API calls made without an Origin header (curl, the test client) are
# unaffected, which is why it only shows up when clicking through the UI.
# local_prod/prod set this from DJANGO_CSRF_TRUSTED_ORIGINS instead.
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
