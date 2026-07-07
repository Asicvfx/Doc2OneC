from rest_framework import serializers

from .models import Document, ProcessingLog


class ProcessingLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessingLog
        fields = ["id", "step", "message", "level", "created_at"]
        read_only_fields = fields


class DocumentSerializer(serializers.ModelSerializer):
    logs = ProcessingLogSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id",
            "title",
            "file",
            "file_url",
            "file_type",
            "status",
            "status_display",
            "extracted_text",
            "normalized_json",
            "validation_errors",
            "uploaded_by",
            "created_at",
            "updated_at",
            "logs",
        ]
        read_only_fields = [
            "id",
            "file_type",
            "status",
            "status_display",
            "extracted_text",
            "normalized_json",
            "validation_errors",
            "uploaded_by",
            "created_at",
            "updated_at",
            "logs",
        ]

    def get_file_url(self, obj) -> str | None:
        if not obj.file:
            return None
        request = self.context.get("request")
        url = obj.file.url
        return request.build_absolute_uri(url) if request else url

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["uploaded_by"] = request.user
        return super().create(validated_data)


class DocumentActionResultSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    status = serializers.CharField()
    normalized_json = serializers.JSONField()
    validation_errors = serializers.JSONField()
