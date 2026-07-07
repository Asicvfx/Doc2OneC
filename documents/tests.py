from pathlib import Path
from tempfile import NamedTemporaryFile

from django.core.files import File
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from directories.models import Employee, WorkObject, WorkType
from documents.models import Document
from documents.services.pipeline import process_document


SAMPLE_TEXT = "Иванов Иван 2026-07-06 Объект №1 Электромонтажные работы 8 часов Монтаж кабеля"


class DemoDirectoryMixin:
    def setUp(self):
        Employee.objects.create(full_name="Иванов Иван", external_1c_id="EMP-001")
        WorkObject.objects.create(name="Объект №1", external_1c_id="OBJ-001")
        WorkType.objects.create(name="Электромонтажные работы", external_1c_id="WT-001")

    def create_uploaded_document(self, name="sample_worklog.txt"):
        with NamedTemporaryFile(suffix=".txt", delete=False, mode="w", encoding="utf-8") as handle:
            handle.write(SAMPLE_TEXT)
            temp_path = Path(handle.name)

        document = Document.objects.create(title="Sample worklog")
        with temp_path.open("rb") as handle:
            document.file.save(name, File(handle), save=True)
        temp_path.unlink(missing_ok=True)
        return document


class DocumentPipelineTests(DemoDirectoryMixin, TestCase):
    def test_process_document_extracts_normalized_ready_for_1c_payload(self):
        document = self.create_uploaded_document()

        process_document(document.id)
        document.refresh_from_db()

        self.assertEqual(document.status, Document.Status.READY_FOR_1C)
        self.assertEqual(document.file_type, Document.FileType.TXT)
        self.assertEqual(
            document.normalized_json,
            {
                "employee_name": "Иванов Иван",
                "date": "2026-07-06",
                "object": "Объект №1",
                "work_type": "Электромонтажные работы",
                "hours": 8,
                "comment": "Монтаж кабеля",
            },
        )
        self.assertEqual(document.validation_errors, [])
        self.assertGreaterEqual(document.logs.count(), 6)


class DocumentApiTests(DemoDirectoryMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def test_api_create_and_process_document(self):
        with NamedTemporaryFile(suffix=".txt", delete=False, mode="w", encoding="utf-8") as handle:
            handle.write(SAMPLE_TEXT)
            temp_path = Path(handle.name)

        with temp_path.open("rb") as handle:
            response = self.client.post(
                "/api/documents/",
                {"title": "API sample", "file": handle},
                format="multipart",
            )
        temp_path.unlink(missing_ok=True)

        self.assertEqual(response.status_code, 201)
        document_id = response.data["id"]

        process_response = self.client.post(f"/api/documents/{document_id}/process/")
        self.assertEqual(process_response.status_code, 200)
        self.assertEqual(process_response.data["status"], Document.Status.READY_FOR_1C)
        self.assertEqual(process_response.data["normalized_json"]["employee_name"], "Иванов Иван")

    def test_export_endpoints_return_downloadable_payloads(self):
        document = self.create_uploaded_document()
        process_document(document.id)

        json_response = self.client.get(reverse("documents:export_json", args=[document.id]))
        csv_response = self.client.get(reverse("documents:export_csv", args=[document.id]))

        self.assertEqual(json_response.status_code, 200)
        self.assertEqual(json_response["Content-Type"], "application/json; charset=utf-8")
        self.assertEqual(csv_response.status_code, 200)
        self.assertEqual(csv_response["Content-Type"], "text/csv; charset=utf-8-sig")

    def test_swagger_and_openapi_schema_are_available(self):
        schema_response = self.client.get("/api/schema/")
        docs_response = self.client.get("/api/docs/")

        self.assertEqual(schema_response.status_code, 200)
        self.assertEqual(docs_response.status_code, 200)
