import threading

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import close_old_connections, transaction

from documents.models import Document
from documents.tasks import process_document_task

from .pipeline import process_document
from .processing_runtime import celery_storage_is_safe, local_file_worker_override_enabled


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

    if mode == "thread":
        _mark_document_queued(document)
        document.logs.create(step="queue", message=f"Processing queued in background thread from {source}.", level="info")
        transaction.on_commit(lambda: _start_background_thread(document.id))
        return document

    if mode == "celery":
        _validate_celery_configuration()
        _mark_document_queued(document)
        message = f"Processing queued in Celery from {source}."
        if local_file_worker_override_enabled() and (settings.FILE_STORAGE_BACKEND or "filesystem").strip().lower() == "filesystem":
            message += " Local filesystem worker override is enabled for same-machine development."
        document.logs.create(step="queue", message=message, level="info")
        transaction.on_commit(lambda: process_document_task.delay(document.id))
        return document

    raise ImproperlyConfigured(
        "Unsupported PROCESSING_MODE. Use one of: sync, thread, celery."
    )


def _mark_document_queued(document: Document) -> None:
    document.status = Document.Status.QUEUED
    document.save(update_fields=["status", "updated_at"])


def _validate_celery_configuration() -> None:
    if settings.CELERY_TASK_ALWAYS_EAGER:
        return
    if not celery_storage_is_safe():
        raise ImproperlyConfigured(
            "PROCESSING_MODE=celery requires FILE_STORAGE_BACKEND=s3 for real separate worker deployment, "
            "or set ALLOW_LOCAL_FILE_WORKER=True only when Django and Celery share the same local filesystem."
        )
    if not (settings.CELERY_BROKER_URL or "").strip():
        raise ImproperlyConfigured(
            "PROCESSING_MODE=celery requires CELERY_BROKER_URL, or enable CELERY_TASK_ALWAYS_EAGER for local checks."
        )


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
