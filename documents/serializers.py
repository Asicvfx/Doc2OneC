from decimal import Decimal

from rest_framework import serializers

from .models import Document, ProcessingLog


class ProcessingLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessingLog
        fields = ["id", "step", "message", "level", "created_at"]
        read_only_fields = fields


class DocumentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ["id", "title", "file"]
        read_only_fields = ["id"]

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["uploaded_by"] = request.user
        return super().create(validated_data)


class DocumentListSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    validation_error_count = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id",
            "title",
            "file_type",
            "status",
            "status_display",
            "validation_error_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_validation_error_count(self, obj) -> int:
        return len(obj.validation_errors or [])


class DocumentDetailSerializer(serializers.ModelSerializer):
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


class WorklogReviewSerializer(serializers.Serializer):
    employee_name = serializers.CharField(max_length=255)
    date = serializers.DateField()
    object = serializers.CharField(max_length=255)
    work_type = serializers.CharField(max_length=255)
    hours = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=Decimal("0.01"), max_value=Decimal("24"))
    comment = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def to_review_data(self) -> dict:
        return {
            "employee_name": self.validated_data["employee_name"],
            "date": self.validated_data["date"].isoformat(),
            "object": self.validated_data["object"],
            "work_type": self.validated_data["work_type"],
            "hours": str(self.validated_data["hours"]),
            "comment": self.validated_data.get("comment") or None,
        }


class DocumentActionResultSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    status = serializers.CharField()
    normalized_json = serializers.JSONField()
    validation_errors = serializers.JSONField()


class ErrorResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
