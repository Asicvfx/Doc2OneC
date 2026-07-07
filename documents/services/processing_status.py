import re
from dataclasses import dataclass

from documents.models import Document


@dataclass(frozen=True)
class ProcessingIssue:
    title: str
    message: str
    detail: str
    retry_label: str = "Retry processing"

    def as_dict(self) -> dict:
        return {
            "title": self.title,
            "message": self.message,
            "detail": self.detail,
            "retry_label": self.retry_label,
        }


def get_processing_issue(document: Document) -> ProcessingIssue | None:
    if document.status != Document.Status.FAILED:
        return None

    detail = _latest_processing_error(document)
    if not detail:
        detail = "Processing failed before a detailed error was recorded."

    safe_detail = _redact_secret_like_values(detail)
    lower_detail = safe_detail.lower()

    if "timeout" in lower_detail or "timed out" in lower_detail:
        return ProcessingIssue(
            title="OpenAI request timed out",
            message="The AI provider did not respond before the configured timeout.",
            detail=safe_detail,
        )
    if "rate limit" in lower_detail or "429" in lower_detail:
        return ProcessingIssue(
            title="OpenAI rate limit reached",
            message="The provider temporarily rejected the request because too many requests were sent.",
            detail=safe_detail,
        )
    if "quota" in lower_detail or "insufficient_quota" in lower_detail or "billing" in lower_detail:
        return ProcessingIssue(
            title="OpenAI quota or billing issue",
            message="The provider rejected the request because the account quota or billing state needs attention.",
            detail=safe_detail,
        )
    if "api_key" in lower_detail or "authentication" in lower_detail or "unauthorized" in lower_detail or "401" in lower_detail:
        return ProcessingIssue(
            title="OpenAI authentication issue",
            message="Check that the local AI API key is present and valid, then retry processing.",
            detail=safe_detail,
        )
    if "model" in lower_detail and ("not found" in lower_detail or "unsupported" in lower_detail or "does not exist" in lower_detail):
        return ProcessingIssue(
            title="OpenAI model issue",
            message="The configured AI model was rejected by the provider. Check AI_MODEL and retry.",
            detail=safe_detail,
        )
    if "invalid json" in lower_detail or "json" in lower_detail:
        return ProcessingIssue(
            title="AI response format issue",
            message="The provider responded, but the response could not be parsed as the expected worklog JSON.",
            detail=safe_detail,
        )

    return ProcessingIssue(
        title="Processing failed",
        message="Review the error detail below, adjust configuration or input if needed, then retry processing.",
        detail=safe_detail,
    )


def get_processing_issue_payload(document: Document) -> dict | None:
    issue = get_processing_issue(document)
    return issue.as_dict() if issue else None


def _latest_processing_error(document: Document) -> str:
    for error in document.validation_errors or []:
        if isinstance(error, dict) and error.get("field") == "processing":
            return str(error.get("message") or "").strip()

    latest_error_log = document.logs.filter(level="error").order_by("-created_at").first()
    return latest_error_log.message.strip() if latest_error_log else ""


def _redact_secret_like_values(message: str) -> str:
    redacted = re.sub(r"sk-[A-Za-z0-9_-]+", "[redacted]", message or "")
    redacted = re.sub(r"(?i)(api[_ -]?key\s*[=:]\s*)\S+", r"\1[redacted]", redacted)
    return redacted