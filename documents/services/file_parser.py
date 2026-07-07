import csv
from io import TextIOWrapper

from openpyxl import load_workbook

from documents.models import Document


PDF_PLACEHOLDER = "PDF extraction placeholder. Real PDF parser can be added here."
OCR_PLACEHOLDER = "OCR placeholder. Real OCR can be added here."


def parse_document_file(document: Document) -> str:
    document.file.open("rb")
    try:
        if document.file_type == Document.FileType.TXT:
            return _parse_text(document.file)
        if document.file_type == Document.FileType.CSV:
            return _parse_csv(document.file)
        if document.file_type == Document.FileType.XLSX:
            return _parse_xlsx(document.file)
        if document.file_type == Document.FileType.PDF:
            return PDF_PLACEHOLDER
        if document.file_type == Document.FileType.IMAGE:
            return OCR_PLACEHOLDER
        return ""
    finally:
        document.file.close()


def _parse_text(file_obj) -> str:
    content = file_obj.read()
    for encoding in ("utf-8-sig", "utf-8", "cp1251"):
        try:
            return content.decode(encoding).strip()
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace").strip()


def _parse_csv(file_obj) -> str:
    wrapper = TextIOWrapper(file_obj, encoding="utf-8-sig", newline="")
    sample = wrapper.read(2048)
    wrapper.seek(0)
    dialect = csv.Sniffer().sniff(sample, delimiters=",;") if sample else csv.excel
    reader = csv.DictReader(wrapper, dialect=dialect)
    rows = []
    for row in reader:
        rows.append("; ".join(f"{key}={value}" for key, value in row.items() if key and value))
    return "\n".join(rows).strip()


def _parse_xlsx(file_obj) -> str:
    workbook = load_workbook(file_obj, data_only=True, read_only=True)
    sheet = workbook.active
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        return ""

    headers = [str(value).strip() if value is not None else "" for value in rows[0]]
    parsed_rows = []
    for row in rows[1:]:
        pairs = []
        for header, value in zip(headers, row):
            if header and value is not None:
                pairs.append(f"{header}={value}")
        if pairs:
            parsed_rows.append("; ".join(pairs))
    return "\n".join(parsed_rows).strip()
