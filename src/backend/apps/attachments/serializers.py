"""Upload validation (FR-104, TECHNICAL_ARCHITECTURE §10): images + PDF only,
size cap, and content sniffing — the declared content type must match the
file's magic bytes, so a renamed executable never lands in storage."""

from rest_framework import serializers

from .models import FileAttachment

MAX_SIZE = 10 * 1024 * 1024  # 10 MB

ALLOWED_MODULES = ("purchases", "sales")

# content-type → magic-byte prefixes
MAGIC_BYTES = {
    "application/pdf": (b"%PDF",),
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/webp": (b"RIFF",),
}


def sniff_content_type(header: bytes) -> str | None:
    for content_type, prefixes in MAGIC_BYTES.items():
        if any(header.startswith(prefix) for prefix in prefixes):
            return content_type
    return None


class FileAttachmentSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True)
    download_url = serializers.SerializerMethodField()
    uploaded_by_username = serializers.CharField(source="uploaded_by.username", read_only=True)

    class Meta:
        model = FileAttachment
        fields = [
            "id",
            "module",
            "record_id",
            "file",
            "original_name",
            "content_type",
            "size",
            "uploaded_by_username",
            "uploaded_at",
            "download_url",
        ]
        read_only_fields = ["original_name", "content_type", "size", "uploaded_at"]

    def get_download_url(self, attachment):
        return f"/api/v1/attachments/{attachment.pk}/download/"

    def validate_module(self, value):
        if value not in ALLOWED_MODULES:
            raise serializers.ValidationError(
                f"Uploads are supported for {', '.join(ALLOWED_MODULES)} only."
            )
        return value

    def validate_file(self, upload):
        if upload.size > MAX_SIZE:
            raise serializers.ValidationError("File is larger than 10 MB.")
        header = upload.read(16)
        upload.seek(0)
        sniffed = sniff_content_type(header)
        if sniffed is None:
            raise serializers.ValidationError(
                "Only PDF, JPEG, PNG, or WebP files are supported."
            )
        self._sniffed_type = sniffed
        return upload

    def validate(self, attrs):
        module, record_id = attrs["module"], attrs["record_id"]
        target = self._target_queryset(module).filter(pk=record_id).first()
        if target is None:
            raise serializers.ValidationError(
                {"record_id": f"No {module} record #{record_id}."}
            )
        attrs["content_type"] = self._sniffed_type
        attrs["original_name"] = attrs["file"].name[:255]
        attrs["size"] = attrs["file"].size
        return attrs

    @staticmethod
    def _target_queryset(module):
        if module == "purchases":
            from apps.purchases.models import Purchase

            return Purchase.objects.filter(is_deleted=False)
        from apps.sales.models import Sale

        return Sale.objects.filter(is_deleted=False)
