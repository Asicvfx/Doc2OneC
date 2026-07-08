from documents.models import Document

from .normalizer import normalize_worklog_data
from .validator import validate_worklog_data


REVIEW_FIELDS = ["employee_name", "date", "object", "work_type", "hours", "comment"]


def apply_manual_review(document: Document, data: dict) -> Document:
    review_data = {field: data.get(field) for field in REVIEW_FIELDS}
    normalized_data = normalize_worklog_data(review_data)
    validation_errors = validate_worklog_data(normalized_data)

    document.normalized_json = normalized_data
    document.validation_errors = validation_errors
    document.status = Document.Status.NEEDS_REVIEW if validation_errors else Document.Status.READY_FOR_1C
    document.save(update_fields=["normalized_json", "validation_errors", "status", "updated_at"])

    if validation_errors:
        document.logs.create(
            step="manual_review",
            message=f"Manual review saved with {len(validation_errors)} validation issue(s).",
            level="warning",
        )
    else:
        document.logs.create(
            step="manual_review",
            message="Data manually reviewed and revalidated.",
            level="info",
        )

    return document
