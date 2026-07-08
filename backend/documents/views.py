import json

from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import DocumentUploadForm, WorklogReviewForm
from .models import Document
from .services.export_status import EXPORT_READY_STATUSES, DocumentNotReadyForExport, mark_document_exported
from .services.exporter import export_document_csv, export_document_json
from .services.manual_review import apply_manual_review
from .services.processing_jobs import (
    ACTIVE_PROCESSING_STATUSES,
    ProcessingAlreadyActive,
    enqueue_document_processing,
    maybe_enqueue_document_processing,
)
from .services.processing_status import get_processing_issue


REFRESH_SECONDS = 5


def document_list(request):
    documents = Document.objects.all()
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()

    if query:
        documents = documents.filter(Q(title__icontains=query) | Q(extracted_text__icontains=query))
    if status:
        documents = documents.filter(status=status)

    active_processing_count = documents.filter(status__in=ACTIVE_PROCESSING_STATUSES).count()
    paginator = Paginator(documents, 12)
    page = paginator.get_page(request.GET.get("page"))
    context = {
        "page": page,
        "query": query,
        "selected_status": status,
        "status_choices": Document.Status.choices,
        "active_processing_count": active_processing_count,
        "has_active_processing": active_processing_count > 0,
        "refresh_seconds": REFRESH_SECONDS,
    }
    return render(request, "documents/document_list.html", context)


def document_upload(request):
    if request.method == "POST":
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            if request.user.is_authenticated:
                document.uploaded_by = request.user
            document.save()
            document = maybe_enqueue_document_processing(document, source="web upload")
            document.refresh_from_db()
            if settings.AUTO_PROCESS_ON_UPLOAD and document.status == Document.Status.QUEUED:
                messages.success(request, "Document uploaded and queued for processing automatically.")
            elif settings.AUTO_PROCESS_ON_UPLOAD and document.status == Document.Status.PROCESSING:
                messages.info(request, "Document uploaded and processing started.")
            elif settings.AUTO_PROCESS_ON_UPLOAD and document.status == Document.Status.READY_FOR_1C:
                messages.success(request, "Document uploaded and processed automatically.")
            elif settings.AUTO_PROCESS_ON_UPLOAD and document.status == Document.Status.NEEDS_REVIEW:
                messages.warning(request, "Document uploaded and processed automatically, but it needs review.")
            elif settings.AUTO_PROCESS_ON_UPLOAD and document.status == Document.Status.FAILED:
                messages.error(request, "Document uploaded, but automatic processing failed.")
            else:
                messages.success(request, "Document uploaded. You can run processing now.")
            return redirect("documents:detail", pk=document.pk)
    else:
        form = DocumentUploadForm()
    return render(request, "documents/document_upload.html", {"form": form, "auto_process_on_upload": settings.AUTO_PROCESS_ON_UPLOAD})


def document_detail(request, pk):
    document = get_object_or_404(Document.objects.prefetch_related("logs"), pk=pk)
    context = {
        "document": document,
        "can_mark_exported": document.status in EXPORT_READY_STATUSES,
        "next_step": _document_next_step(document),
        "processing_issue": get_processing_issue(document),
        "processing_active": document.status in ACTIVE_PROCESSING_STATUSES,
        "normalized_json_pretty": json.dumps(
            document.normalized_json or {},
            ensure_ascii=False,
            indent=2,
        ),
    }
    return render(request, "documents/document_detail.html", context)


def document_review(request, pk):
    document = get_object_or_404(Document.objects.prefetch_related("logs"), pk=pk)
    if request.method == "POST":
        form = WorklogReviewForm(request.POST, document=document)
        if form.is_valid():
            apply_manual_review(document, form.to_review_data())
            document.refresh_from_db()
            if document.status == Document.Status.READY_FOR_1C:
                messages.success(request, "Reviewed data is valid and ready for 1C.")
            else:
                messages.warning(request, "Reviewed data was saved, but validation still needs attention.")
            return redirect("documents:detail", pk=document.pk)
    else:
        form = WorklogReviewForm(document=document)

    context = {
        "document": document,
        "form": form,
        "normalized_json_pretty": json.dumps(document.normalized_json or {}, ensure_ascii=False, indent=2),
    }
    return render(request, "documents/document_review.html", context)


@require_POST
def process_document_view(request, pk):
    document = get_object_or_404(Document, pk=pk)
    try:
        document = enqueue_document_processing(document.id, source="web")
    except ProcessingAlreadyActive:
        messages.info(request, "Processing is already queued or running.")
        return redirect("documents:detail", pk=document.pk)

    document.refresh_from_db()
    if document.status == Document.Status.QUEUED:
        messages.success(request, "Processing queued. Refresh the page to follow progress.")
    elif document.status == Document.Status.PROCESSING:
        messages.info(request, "Processing is running.")
    elif document.status == Document.Status.READY_FOR_1C:
        messages.success(request, "Document processed and ready for 1C export.")
    elif document.status == Document.Status.NEEDS_REVIEW:
        messages.warning(request, "Document processed, but it needs review.")
    else:
        issue = get_processing_issue(document)
        messages.error(request, issue.title if issue else "Processing failed.")
    return redirect("documents:detail", pk=document.pk)


def export_json_view(request, pk):
    document = get_object_or_404(Document, pk=pk)
    return export_document_json(document)


def export_csv_view(request, pk):
    document = get_object_or_404(Document, pk=pk)
    return export_document_csv(document)


@require_POST
def mark_exported_view(request, pk):
    document = get_object_or_404(Document, pk=pk)
    try:
        mark_document_exported(document, source="web")
    except DocumentNotReadyForExport as exc:
        messages.warning(request, str(exc))
    else:
        messages.success(request, "Document marked as exported.")
    return redirect("documents:detail", pk=document.pk)


def _document_next_step(document: Document) -> dict:
    if document.status == Document.Status.UPLOADED:
        return {
            "variant": "info",
            "icon": "bi-play-circle",
            "title": "Run processing",
            "message": "Parse the file, extract worklog data, and validate it before export.",
        }
    if document.status == Document.Status.QUEUED:
        return {
            "variant": "info",
            "icon": "bi-clock-history",
            "title": "Processing queued",
            "message": "The document is waiting for background processing. Refresh this page to follow progress.",
        }
    if document.status == Document.Status.PROCESSING:
        return {
            "variant": "info",
            "icon": "bi-hourglass-split",
            "title": "Processing in progress",
            "message": "The document is currently being prepared for validation.",
        }
    if document.status == Document.Status.NEEDS_REVIEW:
        return {
            "variant": "warning",
            "icon": "bi-pencil-square",
            "title": "Review required",
            "message": "Fix validation issues, save the review, then export when ready.",
        }
    if document.status == Document.Status.READY_FOR_1C:
        return {
            "variant": "success",
            "icon": "bi-check2-circle",
            "title": "Ready for 1C",
            "message": "The document passed validation and can be marked as exported after download or 1C handoff.",
        }
    if document.status == Document.Status.EXPORTED:
        return {
            "variant": "done",
            "icon": "bi-box-arrow-up-right",
            "title": "Exported",
            "message": "This document has already been marked as exported.",
        }
    return {
        "variant": "danger",
        "icon": "bi-exclamation-triangle",
        "title": "Processing failed",
        "message": "Review the processing issue, then retry processing when ready.",
    }