from celery import shared_task
from django.db import close_old_connections

from .services.pipeline import process_document


@shared_task(name="documents.process_document")
def process_document_task(document_id: int):
    close_old_connections()
    try:
        process_document(document_id)
    finally:
        close_old_connections()