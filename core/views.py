from django.db.models import Count
from django.shortcuts import render

from documents.models import Document
from documents.services.processing_jobs import ACTIVE_PROCESSING_STATUSES


REFRESH_SECONDS = 5


def dashboard(request):
    status_counts = {
        row["status"]: row["count"]
        for row in Document.objects.values("status").annotate(count=Count("id"))
    }
    active_processing_count = sum(status_counts.get(status, 0) for status in ACTIVE_PROCESSING_STATUSES)
    stat_cards = [
        ("Total documents", Document.objects.count(), "bg-body"),
        ("Uploaded", status_counts.get(Document.Status.UPLOADED, 0), "bg-body"),
        ("Queued", status_counts.get(Document.Status.QUEUED, 0), "bg-info-subtle"),
        ("Processing", status_counts.get(Document.Status.PROCESSING, 0), "bg-body"),
        ("Needs review", status_counts.get(Document.Status.NEEDS_REVIEW, 0), "bg-warning-subtle"),
        ("Ready for 1C", status_counts.get(Document.Status.READY_FOR_1C, 0), "bg-success-subtle"),
        ("Exported", status_counts.get(Document.Status.EXPORTED, 0), "bg-body"),
        ("Failed", status_counts.get(Document.Status.FAILED, 0), "bg-danger-subtle"),
    ]
    context = {
        "total_documents": Document.objects.count(),
        "stat_cards": stat_cards,
        "recent_documents": Document.objects.order_by("-created_at")[:8],
        "active_processing_count": active_processing_count,
        "has_active_processing": active_processing_count > 0,
        "refresh_seconds": REFRESH_SECONDS,
    }
    return render(request, "core/dashboard.html", context)