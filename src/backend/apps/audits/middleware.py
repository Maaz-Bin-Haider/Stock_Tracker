"""Request context for audit writes (TECHNICAL_ARCHITECTURE §7).

Services deep in the call stack can attribute audit rows to the current
request without threading it through every signature.
"""

import contextvars

_current_request = contextvars.ContextVar("audit_current_request", default=None)


class AuditRequestMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = _current_request.set(request)
        try:
            return self.get_response(request)
        finally:
            _current_request.reset(token)


def get_current_request():
    return _current_request.get()
