from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source="user.username", read_only=True, default="")

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "user",
            "user_username",
            "action",
            "module",
            "record_id",
            "record_repr",
            "before_values",
            "after_values",
            "ip_address",
            "created_at",
        ]
