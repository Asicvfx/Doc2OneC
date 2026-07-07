from django.conf import settings
from django.db import models


class Document(models.Model):
    class FileType(models.TextChoices):
        TXT = "txt", "TXT"
        CSV = "csv", "CSV"
        XLSX = "xlsx", "XLSX"
        PDF = "pdf", "PDF"
        IMAGE = "image", "Image"
        UNKNOWN = "unknown", "Unknown"

    class Status(models.TextChoices):
        UPLOADED = "uploaded", "Uploaded"
        PROCESSING = "processing", "Processing"
        NEEDS_REVIEW = "needs_review", "Needs review"
        READY_FOR_1C = "ready_for_1c", "Ready for 1C"
        EXPORTED = "exported", "Exported"
        FAILED = "failed", "Failed"

    title = models.CharField(max_length=255)
    file = models.FileField(upload_to="documents/%Y/%m/%d/")
    file_type = models.CharField(
        max_length=20,
        choices=FileType.choices,
        default=FileType.UNKNOWN,
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.UPLOADED,
        db_index=True,
    )
    extracted_text = models.TextField(blank=True)
    normalized_json = models.JSONField(default=dict, blank=True)
    validation_errors = models.JSONField(default=list, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="uploaded_documents",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["file_type", "-created_at"]),
        ]

    def __str__(self):
        return self.title

    @property
    def status_badge_class(self):
        return {
            self.Status.UPLOADED: "secondary",
            self.Status.PROCESSING: "primary",
            self.Status.NEEDS_REVIEW: "warning",
            self.Status.READY_FOR_1C: "success",
            self.Status.EXPORTED: "dark",
            self.Status.FAILED: "danger",
        }.get(self.status, "secondary")


class ProcessingLog(models.Model):
    class Level(models.TextChoices):
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        ERROR = "error", "Error"

    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="logs")
    step = models.CharField(max_length=120)
    message = models.TextField()
    level = models.CharField(max_length=20, choices=Level.choices, default=Level.INFO)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["document", "created_at"])]

    def __str__(self):
        return f"{self.document_id}: {self.step}"
