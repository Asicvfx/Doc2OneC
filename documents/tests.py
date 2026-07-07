import json
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

    def valid_review_payload(self, **overrides):
        payload = {
            "employee_name": "Иванов Иван",
            "date": "2026-07-06",
            "object": "Объект №1",
            "work_type": "Электромонтажные работы",
            "hours": "7.5",
            "comment": "Reviewed cable installation",
        }
        payload.update(overrides)
        return payload


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

    def test_api_review_updates_normalized_data_and_revalidates(self):
        document = self.create_uploaded_document()
        process_document(document.id)

        response = self.client.post(
            f"/api/documents/{document.id}/review/",
            self.valid_review_payload(hours="6", comment="Adjusted after review"),
            format="multipart",
        )
        document.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], Document.Status.READY_FOR_1C)
        self.assertEqual(document.normalized_json["hours"], 6)
        self.assertEqual(document.normalized_json["comment"], "Adjusted after review")
        self.assertEqual(document.validation_errors, [])
        self.assertTrue(document.logs.filter(step="manual_review").exists())

    def test_web_review_form_updates_normalized_data_and_revalidates(self):
        document = self.create_uploaded_document()
        process_document(document.id)

        detail_response = self.client.get(reverse("documents:detail", args=[document.id]))
        self.assertContains(detail_response, "Review / Edit data")

        response = self.client.post(
            reverse("documents:review", args=[document.id]),
            self.valid_review_payload(hours="7.25", comment="Reviewed in web UI"),
        )
        document.refresh_from_db()

        self.assertRedirects(response, reverse("documents:detail", args=[document.id]))
        self.assertEqual(document.status, Document.Status.READY_FOR_1C)
        self.assertEqual(document.normalized_json["hours"], 7.25)
        self.assertEqual(document.normalized_json["comment"], "Reviewed in web UI")
        self.assertEqual(document.validation_errors, [])

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

    def test_openapi_document_upload_uses_binary_file_field(self):
        response = self.client.get("/api/schema/?format=json")

        self.assertEqual(response.status_code, 200)
        schema = json.loads(response.content)
        upload_schema = schema["paths"]["/api/documents/"]["post"]["requestBody"]["content"][
            "multipart/form-data"
        ]["schema"]
        component_name = upload_schema["$ref"].split("/")[-1]
        file_property = schema["components"]["schemas"][component_name]["properties"]["file"]

        self.assertEqual(file_property["type"], "string")
        self.assertEqual(file_property["format"], "binary")

    def test_openapi_document_actions_have_expected_request_bodies(self):
        response = self.client.get("/api/schema/?format=json")

        self.assertEqual(response.status_code, 200)
        schema = json.loads(response.content)
        paths = schema["paths"]

        self.assertNotIn("requestBody", paths["/api/documents/{id}/process/"]["post"])
        self.assertNotIn("requestBody", paths["/api/documents/{id}/mark-exported/"]["post"])
        self.assertIn("requestBody", paths["/api/documents/{id}/review/"]["post"])

    def test_api_mark_exported_rejects_unready_document(self):
        document = self.create_uploaded_document()

        response = self.client.post(f"/api/documents/{document.id}/mark-exported/")
        document.refresh_from_db()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(document.status, Document.Status.UPLOADED)
        self.assertIn("ready for 1C", response.data["detail"])

    def test_api_mark_exported_accepts_ready_document(self):
        document = self.create_uploaded_document()
        process_document(document.id)

        response = self.client.post(f"/api/documents/{document.id}/mark-exported/")
        document.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(document.status, Document.Status.EXPORTED)
        self.assertTrue(document.logs.filter(step="export").exists())

    def test_detail_page_guides_unready_and_ready_export_states(self):
        document = self.create_uploaded_document()

        unready_response = self.client.get(reverse("documents:detail", args=[document.id]))
        self.assertContains(unready_response, "Run processing")
        self.assertContains(unready_response, "Export requires ready status")

        process_document(document.id)
        ready_response = self.client.get(reverse("documents:detail", args=[document.id]))
        self.assertContains(ready_response, "Ready for 1C")
        self.assertContains(ready_response, "Mark as exported")

    def test_api_document_list_is_paginated_and_filterable(self):
        ready = Document.objects.create(title="Ready Alpha", status=Document.Status.READY_FOR_1C, file_type=Document.FileType.TXT)
        Document.objects.create(title="Needs Beta", status=Document.Status.NEEDS_REVIEW, file_type=Document.FileType.CSV)
        Document.objects.create(title="Ready Gamma", status=Document.Status.READY_FOR_1C, file_type=Document.FileType.XLSX)

        response = self.client.get("/api/documents/?status=ready_for_1c&search=Ready&ordering=title")

        self.assertEqual(response.status_code, 200)
        self.assertIn("count", response.data)
        self.assertIn("results", response.data)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual([item["title"] for item in response.data["results"]], ["Ready Alpha", "Ready Gamma"])
        self.assertEqual(response.data["results"][0]["id"], ready.id)

    def test_api_create_document_returns_detail_contract(self):
        with NamedTemporaryFile(suffix=".txt", delete=False, mode="w", encoding="utf-8") as handle:
            handle.write(SAMPLE_TEXT)
            temp_path = Path(handle.name)

        with temp_path.open("rb") as handle:
            response = self.client.post(
                "/api/documents/",
                {"title": "Contract upload", "file": handle},
                format="multipart",
            )
        temp_path.unlink(missing_ok=True)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["title"], "Contract upload")
        self.assertEqual(response.data["status"], Document.Status.UPLOADED)
        self.assertIn("file_url", response.data)
        self.assertIn("logs", response.data)

    def test_openapi_document_list_exposes_query_parameters(self):
        response = self.client.get("/api/schema/?format=json")

        self.assertEqual(response.status_code, 200)
        schema = json.loads(response.content)
        parameters = schema["paths"]["/api/documents/"]["get"].get("parameters", [])
        names = {parameter["name"] for parameter in parameters}

        self.assertTrue({"status", "file_type", "search", "ordering"}.issubset(names))
