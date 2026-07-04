from .middleware import get_current_request
from .models import AuditLog


def record_audit(
    *,
    action,
    module="",
    record_id=None,
    record_repr="",
    before=None,
    after=None,
    user=None,
    request=None,
):
    """Write one audit row, attributing it to the current request when available.

    Called explicitly (not via signals) so business intent and before/after
    snapshots are captured reliably, including on bulk paths
    (TECHNICAL_ARCHITECTURE §7).
    """
    request = request or get_current_request()
    ip_address = None
    user_agent = ""
    session_key = ""
    if request is not None:
        if user is None and getattr(request, "user", None) is not None:
            user = request.user if request.user.is_authenticated else None
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        ip_address = (
            forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR")
        )
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:512]
        session = getattr(request, "session", None)
        session_key = getattr(session, "session_key", "") or ""

    return AuditLog.objects.create(
        user=user,
        action=action,
        module=module,
        record_id=record_id,
        record_repr=record_repr[:255],
        before_values=before,
        after_values=after,
        ip_address=ip_address,
        user_agent=user_agent,
        session_key=session_key,
    )
