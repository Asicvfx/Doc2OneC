from pathlib import Path

from documents.models import Document


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


def detect_file_type(file_name: str) -> str:
    suffix = Path(file_name or "").suffix.lower()
    if suffix == ".txt":
        return Document.FileType.TXT
    if suffix == ".csv":
        return Document.FileType.CSV
    if suffix == ".xlsx":
        return Document.FileType.XLSX
    if suffix == ".pdf":
        return Document.FileType.PDF
    if suffix in IMAGE_EXTENSIONS:
        return Document.FileType.IMAGE
    return Document.FileType.UNKNOWN
