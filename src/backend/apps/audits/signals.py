from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

from .models import AuditLog
from .services import record_audit


@receiver(user_logged_in)
def audit_login(sender, request, user, **kwargs):
    record_audit(action=AuditLog.Action.LOGIN, module="auth", user=user, request=request)


@receiver(user_logged_out)
def audit_logout(sender, request, user, **kwargs):
    if user is not None:
        record_audit(action=AuditLog.Action.LOGOUT, module="auth", user=user, request=request)


@receiver(user_login_failed)
def audit_login_failed(sender, credentials, request, **kwargs):
    record_audit(
        action=AuditLog.Action.LOGIN_FAILED,
        module="auth",
        record_repr=str(credentials.get("username", ""))[:255],
        user=None,
        request=request,
    )
