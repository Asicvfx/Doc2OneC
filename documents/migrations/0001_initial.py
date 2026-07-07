# Generated for Doc2OneC MVP.
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Document",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("file", models.FileField(upload_to="documents/%Y/%m/%d/")),
                (
                    "file_type",
                    models.CharField(
                        choices=[
                            ("txt", "TXT"),
                            ("csv", "CSV"),
                            ("xlsx", "XLSX"),
                            ("pdf", "PDF"),
                            ("image", "Image"),
                            ("unknown", "Unknown"),
                        ],
                        default="unknown",
                        max_length=20,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("uploaded", "Uploaded"),
                            ("processing", "Processing"),
                            ("needs_review", "Needs review"),
                            ("ready_for_1c", "Ready for 1C"),
                            ("exported", "Exported"),
                            ("failed", "Failed"),
                        ],
                        db_index=True,
                        default="uploaded",
                        max_length=32,
                    ),
                ),
                ("extracted_text", models.TextField(blank=True)),
                ("normalized_json", models.JSONField(blank=True, default=dict)),
                ("validation_errors", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "uploaded_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="uploaded_documents",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["status", "-created_at"], name="documents_d_status_dead80_idx"),
                    models.Index(fields=["file_type", "-created_at"], name="documents_d_file_ty_4191d3_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="ProcessingLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("step", models.CharField(max_length=120)),
                ("message", models.TextField()),
                (
                    "level",
                    models.CharField(
                        choices=[("info", "Info"), ("warning", "Warning"), ("error", "Error")],
                        default="info",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "document",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="logs",
                        to="documents.document",
                    ),
                ),
            ],
            options={
                "ordering": ["created_at"],
                "indexes": [models.Index(fields=["document", "created_at"], name="documents_p_documen_008fd8_idx")],
            },
        ),
    ]
