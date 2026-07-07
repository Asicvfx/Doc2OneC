from documents.models import Document


EXPORT_READY_STATUSES = {Document.Status.READY_FOR_1C, Document.Status.EXPORTED}


class DocumentNotReadyForExport(ValueError):
    pass


def mark_document_exported(document: Document, *, source: str = "web") -> Document:
    if document.status not in EXPORT_READY_STATUSES:
        raise DocumentNotReadyForExport("Document must be ready for 1C before it can be marked as exported.")

    if document.status == Document.Status.EXPORTED:
        return document

    document.status = Document.Status.EXPORTED
    document.save(update_fields=["status", "updated_at"])
    document.logs.create(step="export", message=f"Document marked as exported via {source}.", level="info")
    return document
