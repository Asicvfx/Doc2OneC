import threading

from django.conf import settings
from django.db import close_old_connections, transaction

from documents.models import Document

from .pipeline import process_document


ACTIVE_PROCESSING_STATUSES = {Document.Status.QUEUED, Document.Status.PROCESSING}


class ProcessingAlreadyActive(Exception):
    pass


def maybe_enqueue_document_processing(document: Document, source: str = "upload") -> Document:
    if not settings.AUTO_PROCESS_ON_UPLOAD:
        return document
    return enqueue_document_processing(document.id, source=source)


def enqueue_document_processing(document_id: int, source: str = "web") -> Document:
    document = Document.objects.get(id=document_id)
    if document.status in ACTIVE_PROCESSING_STATUSES:
        document.logs.create(
            step="queue",
            message="Processing request ignored because the document is already queued or processing.",
            level="warning",
        )
        raise ProcessingAlreadyActive("Document is already queued or processing.")

    mode = (settings.PROCESSING_MODE or "thread").strip().lower()
    if mode == "sync":
        document.logs.create(step="queue", message=f"Processing started synchronously from {source}.", level="info")
        return process_document(document.id)

    document.status = Document.Status.QUEUED
    document.save(update_fields=["status", "updated_at"])
    document.logs.create(step="queue", message=f"Processing queued from {source}.", level="info")
    transaction.on_commit(lambda: _start_background_thread(document.id))
    return document


def _start_background_thread(document_id: int) -> None:
    thread = threading.Thread(
        target=_run_processing_in_thread,
        args=(document_id,),
        daemon=True,
        name=f"doc2onec-process-{document_id}",
    )
    thread.start()


def _run_processing_in_thread(document_id: int) -> None:
    close_old_connections()
    try:
        process_document(document_id)
    finally:
        close_old_connections()