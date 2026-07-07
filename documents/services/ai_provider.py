import json
from dataclasses import dataclass
from typing import Any

from django.conf import settings

from .ai_extractor import extract_worklog_data


WORKLOG_FIELDS = ["employee_name", "date", "object", "work_type", "hours", "comment"]

WORKLOG_EXTRACTION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "employee_name": {"type": ["string", "null"]},
        "date": {
            "type": ["string", "null"],
            "description": "Work date in YYYY-MM-DD format when present.",
        },
        "object": {"type": ["string", "null"]},
        "work_type": {"type": ["string", "null"]},
        "hours": {
            "type": ["string", "number", "null"],
            "description": "Worked hours as a number or short phrase from the source document.",
        },
        "comment": {"type": ["string", "null"]},
    },
    "required": WORKLOG_FIELDS,
}

WORKLOG_EXTRACTION_INSTRUCTIONS = """
Extract employee worklog data for import into 1C.
Return only the fields from the JSON schema.
Use the source language for names, objects, work types, and comments.
If a field is missing or uncertain, return null for that field.
Do not invent employees, dates, objects, work types, or hours.
""".strip()


class AIProviderError(Exception):
    pass


@dataclass(frozen=True)
class MockAIProvider:
    name: str = "mock"

    def extract(self, text: str) -> dict:
        return extract_worklog_data(text)


@dataclass(frozen=True)
class OpenAIProvider:
    name: str = "openai"
    api_key: str = ""
    model: str = "gpt-5.5"
    timeout: float = 30.0
    client: Any | None = None

    def extract(self, text: str) -> dict:
        if not self.api_key:
            raise AIProviderError("AI_PROVIDER=openai requires AI_API_KEY in the environment.")
        if not (text or "").strip():
            return _empty_worklog_data()

        client = self.client or self._build_client()
        try:
            response = client.responses.create(
                model=self.model,
                instructions=WORKLOG_EXTRACTION_INSTRUCTIONS,
                input=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": _trim_input(text),
                            }
                        ],
                    }
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "worklog_extraction",
                        "schema": WORKLOG_EXTRACTION_SCHEMA,
                        "strict": True,
                    }
                },
            )
        except Exception as exc:
            raise AIProviderError(f"OpenAI extraction failed: {self._safe_error_message(exc)}") from exc

        return _parse_openai_json(response.output_text)

    def _build_client(self):
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise AIProviderError("OpenAI provider requires the 'openai' Python package.") from exc
        return OpenAI(api_key=self.api_key, timeout=self.timeout)

    def _safe_error_message(self, exc: Exception) -> str:
        message = str(exc) or exc.__class__.__name__
        if self.api_key:
            message = message.replace(self.api_key, "[redacted]")
        return message


def get_ai_provider(provider_name: str | None = None):
    provider = (provider_name or settings.AI_PROVIDER or "mock").strip().lower()
    if provider == "mock":
        return MockAIProvider()
    if provider == "openai":
        return OpenAIProvider(
            api_key=settings.AI_API_KEY,
            model=settings.AI_MODEL,
            timeout=settings.AI_TIMEOUT,
        )
    raise AIProviderError(f"Unsupported AI_PROVIDER '{provider}'. Use 'mock' or 'openai'.")


def _parse_openai_json(output_text: str) -> dict:
    try:
        payload = json.loads(output_text)
    except json.JSONDecodeError as exc:
        raise AIProviderError("OpenAI extraction returned invalid JSON.") from exc

    if not isinstance(payload, dict):
        raise AIProviderError("OpenAI extraction returned JSON that is not an object.")

    return {field: payload.get(field) for field in WORKLOG_FIELDS}


def _empty_worklog_data() -> dict:
    return {field: None for field in WORKLOG_FIELDS}


def _trim_input(text: str, max_chars: int = 12000) -> str:
    clean_text = (text or "").strip()
    if len(clean_text) <= max_chars:
        return clean_text
    return clean_text[:max_chars]
