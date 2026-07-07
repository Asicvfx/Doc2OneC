from django.db import transaction

from documents.models import Document

from .ai_extractor import extract_worklog_data
from .file_detector import detect_file_type
from .file_parser import parse_document_file
from .normalizer import normalize_worklog_data
from .one_c_adapter import OneCAdapter
from .validator import validate_worklog_data


def process_document(document_id: int) -> Document:
    document = Document.objects.get(id=document_id)
    document.status = Document.Status.PROCESSING
    document.save(update_fields=["status", "updated_at"])
    document.logs.create(step="start", message="Processing started.", level="info")

    try:
        with transaction.atomic():
            file_type = detect_file_type(document.file.name)
            document.file_type = file_type
            document.logs.create(step="detect_file_type", message=f"Detected file type: {file_type}.", level="info")

            extracted_text = parse_document_file(document)
            document.extracted_text = extracted_text
            document.logs.create(step="parse", message="File content parsed.", level="info")

            extracted_data = extract_worklog_data(extracted_text)
            document.logs.create(step="extract", message="Mock AI extraction completed.", level="info")

            normalized_data = normalize_worklog_data(extracted_data)
            document.normalized_json = normalized_data
            document.logs.create(step="normalize", message="Data normalized into stable JSON.", level="info")

            validation_errors = validate_worklog_data(normalized_data)
            document.validation_errors = validation_errors
            if validation_errors:
                document.status = Document.Status.NEEDS_REVIEW
                document.logs.create(
                    step="validate",
                    message=f"Validation completed with {len(validation_errors)} issue(s).",
                    level="warning",
                )
            else:
                OneCAdapter().prepare_payload(normalized_data)
                document.status = Document.Status.READY_FOR_1C
                document.logs.create(step="validate", message="Validation passed.", level="info")
                document.logs.create(step="one_c", message="1C payload prepared in mock mode.", level="info")

            document.save(
                update_fields=[
                    "file_type",
                    "status",
                    "extracted_text",
                    "normalized_json",
                    "validation_errors",
                    "updated_at",
                ]
            )
    except Exception as exc:
        document.status = Document.Status.FAILED
        document.validation_errors = [{"field": "processing", "message": str(exc)}]
        document.save(update_fields=["status", "validation_errors", "updated_at"])
        document.logs.create(step="failed", message=str(exc), level="error")

    return document
