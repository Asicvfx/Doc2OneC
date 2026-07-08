from django.db import connections
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import render

from documents.models import Document
from documents.services.processing_jobs import ACTIVE_PROCESSING_STATUSES
from documents.services.processing_runtime import get_processing_runtime_status


REFRESH_SECONDS = 5


def dashboard(request):
    status_counts = {
        row["status"]: row["count"]
        for row in Document.objects.values("status").annotate(count=Count("id"))
    }
    active_processing_count = sum(status_counts.get(status, 0) for status in ACTIVE_PROCESSING_STATUSES)
    runtime_status = get_processing_runtime_status()
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
        "runtime_status": runtime_status,
    }
    return render(request, "core/dashboard.html", context)


def processing_runtime_status_view(request):
    status = get_processing_runtime_status()
    return JsonResponse(status.as_dict())


def healthcheck_view(request):
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception as exc:
        return JsonResponse({"status": "error", "database": "down", "detail": str(exc)}, status=503)

    return JsonResponse({"status": "ok", "database": "up"})