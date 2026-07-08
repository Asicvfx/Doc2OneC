from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings

from documents.models import Document


@dataclass(frozen=True)
class ProcessingRuntimeStatus:
    mode: str
    auto_process_on_upload: bool
    broker_configured: bool
    eager: bool
    worker_status: str
    worker_detail: str

    def as_dict(self) -> dict:
        return {
            "mode": self.mode,
            "auto_process_on_upload": self.auto_process_on_upload,
            "broker_configured": self.broker_configured,
            "eager": self.eager,
            "worker_status": self.worker_status,
            "worker_detail": self.worker_detail,
            "active_statuses": list(ACTIVE_PROCESSING_STATUSES),
        }


ACTIVE_PROCESSING_STATUSES = [Document.Status.QUEUED, Document.Status.PROCESSING]


def get_processing_runtime_status() -> ProcessingRuntimeStatus:
    mode = (settings.PROCESSING_MODE or "thread").strip().lower()
    auto_process = bool(settings.AUTO_PROCESS_ON_UPLOAD)
    broker_configured = bool((settings.CELERY_BROKER_URL or "").strip())
    eager = bool(settings.CELERY_TASK_ALWAYS_EAGER)

    if mode == "sync":
        return ProcessingRuntimeStatus(
            mode=mode,
            auto_process_on_upload=auto_process,
            broker_configured=broker_configured,
            eager=eager,
            worker_status="not_required",
            worker_detail="Synchronous mode runs inside the web request. No background worker is needed.",
        )

    if mode == "thread":
        return ProcessingRuntimeStatus(
            mode=mode,
            auto_process_on_upload=auto_process,
            broker_configured=broker_configured,
            eager=eager,
            worker_status="not_required",
            worker_detail="Thread mode runs inside the Django process. No Redis or Celery worker is needed.",
        )

    if mode != "celery":
        return ProcessingRuntimeStatus(
            mode=mode,
            auto_process_on_upload=auto_process,
            broker_configured=broker_configured,
            eager=eager,
            worker_status="misconfigured",
            worker_detail="Unsupported PROCESSING_MODE. Use sync, thread, or celery.",
        )

    if eager:
        return ProcessingRuntimeStatus(
            mode=mode,
            auto_process_on_upload=auto_process,
            broker_configured=broker_configured,
            eager=eager,
            worker_status="eager",
            worker_detail="Celery eager mode is enabled. Tasks execute immediately in-process for local checks.",
        )

    if not broker_configured:
        return ProcessingRuntimeStatus(
            mode=mode,
            auto_process_on_upload=auto_process,
            broker_configured=broker_configured,
            eager=eager,
            worker_status="misconfigured",
            worker_detail="Celery mode is selected, but CELERY_BROKER_URL is empty.",
        )

    return _probe_celery_worker(
        mode=mode,
        auto_process=auto_process,
        broker_configured=broker_configured,
        eager=eager,
    )


def _probe_celery_worker(*, mode: str, auto_process: bool, broker_configured: bool, eager: bool) -> ProcessingRuntimeStatus:
    try:
        from doc2onec.celery import app as celery_app

        inspect = celery_app.control.inspect(timeout=1.0)
        ping_result = inspect.ping() if inspect else None
    except Exception as exc:
        return ProcessingRuntimeStatus(
            mode=mode,
            auto_process_on_upload=auto_process,
            broker_configured=broker_configured,
            eager=eager,
            worker_status="offline",
            worker_detail=f"Celery ping failed: {exc}",
        )

    if ping_result:
        workers = ", ".join(sorted(ping_result.keys()))
        return ProcessingRuntimeStatus(
            mode=mode,
            auto_process_on_upload=auto_process,
            broker_configured=broker_configured,
            eager=eager,
            worker_status="online",
            worker_detail=f"Celery worker responded: {workers}",
        )

    return ProcessingRuntimeStatus(
        mode=mode,
        auto_process_on_upload=auto_process,
        broker_configured=broker_configured,
        eager=eager,
        worker_status="offline",
        worker_detail="Broker is configured, but no Celery worker responded to ping.",
    )