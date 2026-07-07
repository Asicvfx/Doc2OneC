import json

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import DocumentUploadForm, WorklogReviewForm
from .models import Document
from .services.exporter import export_document_csv, export_document_json
from .services.manual_review import apply_manual_review
from .services.pipeline import process_document


def document_list(request):
    documents = Document.objects.all()
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()

    if query:
        documents = documents.filter(Q(title__icontains=query) | Q(extracted_text__icontains=query))
    if status:
        documents = documents.filter(status=status)

    paginator = Paginator(documents, 12)
    page = paginator.get_page(request.GET.get("page"))
    context = {
        "page": page,
        "query": query,
        "selected_status": status,
        "status_choices": Document.Status.choices,
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
            messages.success(request, "Document uploaded. You can run processing now.")
            return redirect("documents:detail", pk=document.pk)
    else:
        form = DocumentUploadForm()
    return render(request, "documents/document_upload.html", {"form": form})


def document_detail(request, pk):
    document = get_object_or_404(Document.objects.prefetch_related("logs"), pk=pk)
    context = {
        "document": document,
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
    process_document(document.id)
    document.refresh_from_db()
    if document.status == Document.Status.READY_FOR_1C:
        messages.success(request, "Document processed and ready for 1C export.")
    elif document.status == Document.Status.NEEDS_REVIEW:
        messages.warning(request, "Document processed, but it needs review.")
    else:
        messages.error(request, "Processing failed.")
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
    document.status = Document.Status.EXPORTED
    document.save(update_fields=["status", "updated_at"])
    document.logs.create(step="export", message="Document marked as exported.", level="info")
    messages.success(request, "Document marked as exported.")
    return redirect("documents:detail", pk=document.pk)
