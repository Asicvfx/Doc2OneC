from django.db.models import Count
from django.shortcuts import render

from documents.models import Document


def dashboard(request):
    status_counts = {
        row["status"]: row["count"]
        for row in Document.objects.values("status").annotate(count=Count("id"))
    }
    stat_cards = [
        ("Total documents", Document.objects.count(), "bg-body"),
        ("Uploaded", status_counts.get(Document.Status.UPLOADED, 0), "bg-body"),
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
    }
    return render(request, "core/dashboard.html", context)
