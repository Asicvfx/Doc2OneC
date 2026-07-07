import base64
import mimetypes
from dataclasses import dataclass
from typing import Any

from django.conf import settings


OCR_DISABLED_MESSAGE = "OCR is disabled. Set OCR_PROVIDER=openai to extract text from images or scanned PDFs."
OCR_EMPTY_MESSAGE = "OCR completed, but no readable text was found."
OCR_INSTRUCTIONS = """
Extract all readable text from this document image.
Return only the text as plain text.
Keep line breaks where they help preserve the document structure.
Do not summarize, translate, or invent missing text.
""".strip()


class OCRError(Exception):
    pass


@dataclass(frozen=True)
class DisabledOCRProvider:
    name: str = "disabled"

    def extract_from_image_bytes(self, image_bytes: bytes, mime_type: str = "image/png") -> str:
        return OCR_DISABLED_MESSAGE


@dataclass(frozen=True)
class OpenAIOCRProvider:
    name: str = "openai"
    api_key: str = ""
    model: str = "gpt-5.5"
    timeout: float = 30.0
    client: Any | None = None

    def extract_from_image_bytes(self, image_bytes: bytes, mime_type: str = "image/png") -> str:
        if not self.api_key:
            raise OCRError("OCR_PROVIDER=openai requires AI_API_KEY in the environment.")
        if not image_bytes:
            return OCR_EMPTY_MESSAGE

        client = self.client or self._build_client()
        data_url = _image_data_url(image_bytes, mime_type)
        try:
            response = client.responses.create(
                model=self.model,
                instructions=OCR_INSTRUCTIONS,
                input=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": "Extract the readable text from this document image."},
                            {"type": "input_image", "image_url": data_url, "detail": "high"},
                        ],
                    }
                ],
            )
        except Exception as exc:
            raise OCRError(f"OpenAI OCR failed: {self._safe_error_message(exc)}") from exc

        text = (response.output_text or "").strip()
        return text or OCR_EMPTY_MESSAGE

    def _build_client(self):
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise OCRError("OpenAI OCR requires the 'openai' Python package.") from exc
        return OpenAI(api_key=self.api_key, timeout=self.timeout)

    def _safe_error_message(self, exc: Exception) -> str:
        message = str(exc) or exc.__class__.__name__
        if self.api_key:
            message = message.replace(self.api_key, "[redacted]")
        return message


def get_ocr_provider(provider_name: str | None = None):
    provider = (provider_name or settings.OCR_PROVIDER or "disabled").strip().lower()
    if provider in {"", "disabled", "none", "off"}:
        return DisabledOCRProvider()
    if provider == "openai":
        return OpenAIOCRProvider(
            api_key=settings.AI_API_KEY,
            model=settings.OCR_MODEL,
            timeout=settings.OCR_TIMEOUT,
        )
    raise OCRError(f"Unsupported OCR_PROVIDER '{provider}'. Use 'openai' or 'disabled'.")


def extract_text_from_image_bytes(image_bytes: bytes, mime_type: str = "image/png") -> str:
    return get_ocr_provider().extract_from_image_bytes(image_bytes, mime_type=mime_type)


def extract_text_from_image_file(file_obj) -> str:
    image_bytes = file_obj.read()
    mime_type = mimetypes.guess_type(getattr(file_obj, "name", ""))[0] or "image/png"
    return extract_text_from_image_bytes(image_bytes, mime_type=mime_type)


def extract_text_from_pdf_page_image(image_bytes: bytes) -> str:
    return extract_text_from_image_bytes(image_bytes, mime_type="image/png")


def _image_data_url(image_bytes: bytes, mime_type: str) -> str:
    encoded = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"
