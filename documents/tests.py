import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from io import BytesIO, StringIO
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.files import File
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from directories.models import Employee, WorkObject, WorkType
from documents.models import Document
from documents.services.ai_provider import AIProviderError, OpenAIProvider
from documents.services.file_parser import parse_document_file
from documents.services.ocr import OCR_DISABLED_MESSAGE, OpenAIOCRProvider
from documents.services.pipeline import process_document
from documents.services.processing_jobs import ProcessingAlreadyActive, enqueue_document_processing
from documents.services.processing_status import get_processing_issue


SAMPLE_TEXT = "Иванов Иван 2026-07-06 Объект №1 Электромонтажные работы 8 часов Монтаж кабеля"
PDF_SAMPLE_TEXT = "Ivanov Ivan 2026-07-06 Object 1 electrical work 8 hours cable installation"




def _build_minimal_pdf(text=None):
    stream = ""
    if text:
        escaped_text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream = f"BT /F1 12 Tf 72 720 Td ({escaped_text}) Tj ET"

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 612 792] /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(stream.encode('latin-1'))} >>\nstream\n{stream}\nendstream".encode("latin-1"),
    ]

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = []
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return bytes(pdf)

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


    def create_pdf_document(self, text=None, name="sample_worklog.pdf"):
        buffer = BytesIO(_build_minimal_pdf(text))
        document = Document.objects.create(title="PDF worklog", file_type=Document.FileType.PDF)
        document.file.save(name, File(buffer), save=True)
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



class FakeOpenAIResponse:
    def __init__(self, output_text):
        self.output_text = output_text


class FakeResponsesResource:
    def __init__(self, output_text):
        self.output_text = output_text
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return FakeOpenAIResponse(self.output_text)


class FakeOpenAIClient:
    def __init__(self, output_text):
        self.responses = FakeResponsesResource(output_text)


class OpenAIProviderTests(TestCase):
    def test_openai_provider_extracts_structured_worklog_json(self):
        client = FakeOpenAIClient(
            json.dumps(
                {
                    "employee_name": "Иванов Иван",
                    "date": "2026-07-06",
                    "object": "Объект №1",
                    "work_type": "Электромонтажные работы",
                    "hours": "8",
                    "comment": "Монтаж кабеля",
                }
            )
        )
        provider = OpenAIProvider(api_key="test-key", model="test-model", client=client)

        result = provider.extract(SAMPLE_TEXT)

        self.assertEqual(result["employee_name"], "Иванов Иван")
        self.assertEqual(result["hours"], "8")
        request = client.responses.calls[0]
        self.assertEqual(request["model"], "test-model")
        self.assertEqual(request["text"]["format"]["type"], "json_schema")
        self.assertEqual(request["text"]["format"]["name"], "worklog_extraction")
        self.assertTrue(request["text"]["format"]["strict"])

    def test_openai_provider_rejects_invalid_json_response(self):
        provider = OpenAIProvider(api_key="test-key", client=FakeOpenAIClient("not json"))

        with self.assertRaisesMessage(AIProviderError, "invalid JSON"):
            provider.extract(SAMPLE_TEXT)

    def test_openai_provider_returns_empty_data_for_empty_text(self):
        provider = OpenAIProvider(api_key="test-key", client=FakeOpenAIClient("{}"))

        result = provider.extract("   ")

        self.assertEqual(
            result,
            {
                "employee_name": None,
                "date": None,
                "object": None,
                "work_type": None,
                "hours": None,
                "comment": None,
            },
        )

    def test_openai_ocr_provider_extracts_text_from_image_bytes(self):
        class FakeOCRResponse:
            output_text = "Иванов Иван 2026-07-06 Объект №1"

        class FakeResponsesResource:
            def __init__(self):
                self.calls = []

            def create(self, **kwargs):
                self.calls.append(kwargs)
                return FakeOCRResponse()

        class FakeClient:
            def __init__(self):
                self.responses = FakeResponsesResource()

        client = FakeClient()
        provider = OpenAIOCRProvider(api_key="test-key", model="test-model", client=client)

        result = provider.extract_from_image_bytes(b"fake-image", mime_type="image/png")

        self.assertIn("Иванов Иван", result)
        request = client.responses.calls[0]
        self.assertEqual(request["model"], "test-model")
        content = request["input"][0]["content"]
        self.assertEqual(content[1]["type"], "input_image")
        self.assertTrue(content[1]["image_url"].startswith("data:image/png;base64,"))

@override_settings(AI_PROVIDER="mock", OCR_PROVIDER="disabled", PROCESSING_MODE="sync")
class DocumentPipelineTests(DemoDirectoryMixin, TestCase):

    def test_parse_pdf_extracts_selectable_text(self):
        document = self.create_pdf_document(text=PDF_SAMPLE_TEXT)

        extracted_text = parse_document_file(document)

        self.assertIn("Ivanov Ivan", extracted_text)
        self.assertIn("electrical work", extracted_text)


    @override_settings(OCR_PROVIDER="openai")
    def test_parse_scanned_pdf_uses_ocr_fallback(self):
        document = self.create_pdf_document(text=None)

        with patch("documents.services.file_parser.extract_text_from_pdf_page_image", return_value="OCR text from page"):
            extracted_text = parse_document_file(document)

        self.assertEqual(extracted_text, "OCR text from page")

    def test_parse_pdf_reports_when_ocr_is_required(self):
        document = self.create_pdf_document(text=None)

        extracted_text = parse_document_file(document)

        self.assertEqual(extracted_text, OCR_DISABLED_MESSAGE)

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
        self.assertTrue(
            document.logs.filter(
                step="extract",
                message="AI extraction completed with provider: mock.",
            ).exists()
        )

    @override_settings(AI_PROVIDER="openai", AI_API_KEY="")
    def test_process_document_fails_clearly_when_openai_key_is_missing(self):
        document = self.create_uploaded_document()

        process_document(document.id)
        document.refresh_from_db()

        self.assertEqual(document.status, Document.Status.FAILED)
        self.assertEqual(document.validation_errors[0]["field"], "processing")
        self.assertIn("AI_API_KEY", document.validation_errors[0]["message"])

    @override_settings(AI_PROVIDER="unknown")
    def test_process_document_fails_clearly_for_unknown_ai_provider(self):
        document = self.create_uploaded_document()

        process_document(document.id)
        document.refresh_from_db()

        self.assertEqual(document.status, Document.Status.FAILED)
        self.assertIn("Unsupported AI_PROVIDER", document.validation_errors[0]["message"])



    def test_processing_issue_redacts_secret_like_values(self):
        document = Document.objects.create(
            title="Failed AI document",
            status=Document.Status.FAILED,
            validation_errors=[
                {
                    "field": "processing",
                    "message": "OpenAI authentication failed: api_key=sk-test-secret",
                }
            ],
        )

        issue = get_processing_issue(document)

        self.assertEqual(issue.title, "OpenAI authentication issue")
        self.assertIn("[redacted]", issue.detail)
        self.assertNotIn("sk-test-secret", issue.detail)



@override_settings(AI_PROVIDER="mock", OCR_PROVIDER="disabled")
class DocumentProcessingQueueTests(DemoDirectoryMixin, TestCase):
    @override_settings(PROCESSING_MODE="thread")
    def test_enqueue_document_processing_marks_document_queued(self):
        document = self.create_uploaded_document()

        with patch("documents.services.processing_jobs._start_background_thread") as start_thread:
            with self.captureOnCommitCallbacks(execute=True):
                queued_document = enqueue_document_processing(document.id, source="test")

        queued_document.refresh_from_db()
        self.assertEqual(queued_document.status, Document.Status.QUEUED)
        self.assertTrue(queued_document.logs.filter(step="queue").exists())
        start_thread.assert_called_once_with(document.id)

    @override_settings(PROCESSING_MODE="thread")
    def test_enqueue_document_processing_rejects_active_document(self):
        document = self.create_uploaded_document()
        document.status = Document.Status.QUEUED
        document.save(update_fields=["status", "updated_at"])

        with self.assertRaises(ProcessingAlreadyActive):
            enqueue_document_processing(document.id, source="test")

        self.assertTrue(document.logs.filter(step="queue", level="warning").exists())

    @override_settings(PROCESSING_MODE="thread")
    def test_api_process_returns_accepted_when_document_is_queued(self):
        document = self.create_uploaded_document()
        client = APIClient()

        with patch("documents.services.processing_jobs._start_background_thread"):
            with self.captureOnCommitCallbacks(execute=True):
                response = client.post(f"/api/documents/{document.id}/process/")

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data["status"], Document.Status.QUEUED)

    def test_detail_page_disables_processing_action_while_queued(self):
        document = self.create_uploaded_document()
        document.status = Document.Status.QUEUED
        document.save(update_fields=["status", "updated_at"])

        response = self.client.get(reverse("documents:detail", args=[document.id]))

        self.assertContains(response, "Processing queued")
        self.assertContains(response, "http-equiv=\"refresh\"")


@override_settings(AI_PROVIDER="mock", OCR_PROVIDER="disabled", PROCESSING_MODE="thread", AUTO_PROCESS_ON_UPLOAD=True)
class DocumentAutoUploadTests(DemoDirectoryMixin, TestCase):
    def test_web_upload_queues_document_automatically(self):
        with NamedTemporaryFile(suffix=".txt", delete=False, mode="w", encoding="utf-8") as handle:
            handle.write(SAMPLE_TEXT)
            temp_path = Path(handle.name)

        with temp_path.open("rb") as handle:
            with patch("documents.services.processing_jobs._start_background_thread") as start_thread:
                with self.captureOnCommitCallbacks(execute=True):
                    response = self.client.post(
                        reverse("documents:upload"),
                        {"title": "Auto web upload", "file": handle},
                        follow=True,
                    )
        temp_path.unlink(missing_ok=True)

        document = Document.objects.get(title="Auto web upload")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(document.status, Document.Status.QUEUED)
        self.assertContains(response, "queued for processing automatically")
        start_thread.assert_called_once_with(document.id)

    def test_api_create_document_queues_when_auto_processing_enabled(self):
        with NamedTemporaryFile(suffix=".txt", delete=False, mode="w", encoding="utf-8") as handle:
            handle.write(SAMPLE_TEXT)
            temp_path = Path(handle.name)

        with temp_path.open("rb") as handle:
            with patch("documents.services.processing_jobs._start_background_thread") as start_thread:
                with self.captureOnCommitCallbacks(execute=True):
                    response = self.client.post(
                        "/api/documents/",
                        {"title": "Auto API upload", "file": handle},
                        format="multipart",
                    )
        temp_path.unlink(missing_ok=True)

        document = Document.objects.get(title="Auto API upload")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], Document.Status.QUEUED)
        self.assertEqual(document.status, Document.Status.QUEUED)
        start_thread.assert_called_once_with(document.id)

@override_settings(AI_PROVIDER="mock", OCR_PROVIDER="disabled", PROCESSING_MODE="sync", AUTO_PROCESS_ON_UPLOAD=False)
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


    def test_detail_page_shows_processing_issue_and_retry_action(self):
        document = self.create_uploaded_document()
        document.status = Document.Status.FAILED
        document.validation_errors = [
            {
                "field": "processing",
                "message": "OpenAI extraction failed: request timed out after 30 seconds",
            }
        ]
        document.save(update_fields=["status", "validation_errors", "updated_at"])

        response = self.client.get(reverse("documents:detail", args=[document.id]))

        self.assertContains(response, "OpenAI request timed out")
        self.assertContains(response, "The AI provider did not respond")
        self.assertContains(response, "Retry processing")
        self.assertNotContains(response, "validation issue(s) need attention")
        self.assertContains(response, "Validation will continue after processing succeeds.")

    @override_settings(AI_PROVIDER="unknown")
    def test_api_process_returns_processing_issue_for_failed_document(self):
        document = self.create_uploaded_document()

        response = self.client.post(f"/api/documents/{document.id}/process/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], Document.Status.FAILED)
        self.assertEqual(response.data["processing_issue"]["title"], "Processing failed")
        self.assertIn("Unsupported AI_PROVIDER", response.data["processing_issue"]["detail"])

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


class DocumentTrackingUxTests(DemoDirectoryMixin, TestCase):
    def test_dashboard_auto_refreshes_when_processing_is_active(self):
        Document.objects.create(title="Queued watch", status=Document.Status.QUEUED, file_type=Document.FileType.TXT)
        Document.objects.create(title="Running watch", status=Document.Status.PROCESSING, file_type=Document.FileType.CSV)

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Currently processing 2 documents")
        self.assertContains(response, "http-equiv=\"refresh\"")
        self.assertContains(response, "Queued")

    def test_document_list_auto_refreshes_only_for_active_results(self):
        Document.objects.create(title="Queued watch", status=Document.Status.QUEUED, file_type=Document.FileType.TXT)
        Document.objects.create(title="Ready watch", status=Document.Status.READY_FOR_1C, file_type=Document.FileType.CSV)

        active_response = self.client.get(reverse("documents:list"))
        ready_response = self.client.get(reverse("documents:list"), {"status": Document.Status.READY_FOR_1C})

        self.assertContains(active_response, "Processing watch: 1 active document")
        self.assertContains(active_response, "http-equiv=\"refresh\"")
        self.assertContains(ready_response, "Ready watch")
        self.assertNotContains(ready_response, "http-equiv=\"refresh\"")

class DirectoryApiTests(DemoDirectoryMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def test_employee_directory_api_supports_search(self):
        response = self.client.get('/api/employees/?search=EMP-001')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['external_1c_id'], 'EMP-001')


class ProcessingModeTests(DemoDirectoryMixin, TestCase):
    @override_settings(PROCESSING_MODE="celery", CELERY_TASK_ALWAYS_EAGER=True)
    @patch("documents.services.processing_jobs.transaction.on_commit", side_effect=lambda callback: callback())
    @patch("documents.services.processing_jobs.process_document_task.delay")
    def test_enqueue_document_processing_dispatches_celery_task(self, delay_mock, on_commit_mock):
        document = self.create_uploaded_document()

        queued_document = enqueue_document_processing(document.id, source="test")
        document.refresh_from_db()

        self.assertEqual(queued_document.status, Document.Status.QUEUED)
        self.assertEqual(document.status, Document.Status.QUEUED)
        delay_mock.assert_called_once_with(document.id)
        on_commit_mock.assert_called_once()
        self.assertTrue(document.logs.filter(step="queue", message__icontains="Celery").exists())

    @override_settings(PROCESSING_MODE="celery", CELERY_BROKER_URL="", CELERY_TASK_ALWAYS_EAGER=False)
    def test_enqueue_document_processing_requires_celery_broker(self):
        document = self.create_uploaded_document()

        with self.assertRaisesMessage(ImproperlyConfigured, "CELERY_BROKER_URL"):
            enqueue_document_processing(document.id, source="test")
        document.refresh_from_db()

        self.assertEqual(document.status, Document.Status.UPLOADED)

    @override_settings(PROCESSING_MODE="bogus")
    def test_enqueue_document_processing_rejects_unknown_mode(self):
        document = self.create_uploaded_document()

        with self.assertRaisesMessage(ImproperlyConfigured, "Unsupported PROCESSING_MODE"):
            enqueue_document_processing(document.id, source="test")
        document.refresh_from_db()

        self.assertEqual(document.status, Document.Status.UPLOADED)

class ProcessingRuntimeTests(DemoDirectoryMixin, TestCase):
    @override_settings(PROCESSING_MODE="thread", AUTO_PROCESS_ON_UPLOAD=True)
    def test_runtime_status_endpoint_reports_thread_mode(self):
        response = self.client.get(reverse("processing-runtime-status"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["mode"], "thread")
        self.assertEqual(payload["worker_status"], "not_required")
        self.assertTrue(payload["auto_process_on_upload"])

    @override_settings(PROCESSING_MODE="celery", CELERY_BROKER_URL="", CELERY_TASK_ALWAYS_EAGER=False)
    def test_runtime_status_endpoint_reports_celery_misconfiguration(self):
        response = self.client.get(reverse("processing-runtime-status"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["mode"], "celery")
        self.assertEqual(payload["worker_status"], "misconfigured")
        self.assertIn("CELERY_BROKER_URL", payload["worker_detail"])

    @override_settings(PROCESSING_MODE="celery", CELERY_TASK_ALWAYS_EAGER=True)
    def test_runtime_check_command_prints_json_status(self):
        stdout = StringIO()

        call_command("check_processing_runtime", stdout=stdout)
        payload = json.loads(stdout.getvalue())

        self.assertEqual(payload["mode"], "celery")
        self.assertEqual(payload["worker_status"], "eager")


class DashboardRuntimeTests(DemoDirectoryMixin, TestCase):
    @override_settings(PROCESSING_MODE="thread")
    def test_dashboard_shows_processing_backend_panel(self):
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Processing backend")
        self.assertContains(response, "Mode: thread")
        self.assertContains(response, "Open runtime JSON")