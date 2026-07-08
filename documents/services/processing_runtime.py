from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings

from documents.models import Document


@dataclass(frozen=True)
class ProcessingRuntimeStatus:
    mode: str
    auto_process_on_upload: bool
    storage_backend: str
    storage_shared: bool
    local_worker_override: bool
    broker_configured: bool
    eager: bool
    worker_status: str
    worker_detail: str

    def as_dict(self) -> dict:
        return {
            "mode": self.mode,
            "auto_process_on_upload": self.auto_process_on_upload,
            "storage_backend": self.storage_backend,
            "storage_shared": self.storage_shared,
            "local_worker_override": self.local_worker_override,
            "broker_configured": self.broker_configured,
            "eager": self.eager,
            "worker_status": self.worker_status,
            "worker_detail": self.worker_detail,
            "active_statuses": list(ACTIVE_PROCESSING_STATUSES),
        }


ACTIVE_PROCESSING_STATUSES = [Document.Status.QUEUED, Document.Status.PROCESSING]


def get_storage_backend() -> str:
    return (getattr(settings, "FILE_STORAGE_BACKEND", "filesystem") or "filesystem").strip().lower()


def is_shared_storage_enabled() -> bool:
    return get_storage_backend() == "s3"


def local_file_worker_override_enabled() -> bool:
    return bool(getattr(settings, "ALLOW_LOCAL_FILE_WORKER", False))


def celery_requires_shared_storage() -> bool:
    mode = (settings.PROCESSING_MODE or "thread").strip().lower()
    return mode == "celery" and not bool(settings.CELERY_TASK_ALWAYS_EAGER)


def celery_storage_is_safe() -> bool:
    return not celery_requires_shared_storage() or is_shared_storage_enabled() or local_file_worker_override_enabled()


def get_processing_runtime_status() -> ProcessingRuntimeStatus:
    mode = (settings.PROCESSING_MODE or "thread").strip().lower()
    auto_process = bool(settings.AUTO_PROCESS_ON_UPLOAD)
    storage_backend = get_storage_backend()
    storage_shared = is_shared_storage_enabled()
    local_worker_override = local_file_worker_override_enabled()
    broker_configured = bool((settings.CELERY_BROKER_URL or "").strip())
    eager = bool(settings.CELERY_TASK_ALWAYS_EAGER)

    if mode == "sync":
        return ProcessingRuntimeStatus(
            mode=mode,
            auto_process_on_upload=auto_process,
            storage_backend=storage_backend,
            storage_shared=storage_shared,
            local_worker_override=local_worker_override,
            broker_configured=broker_configured,
            eager=eager,
            worker_status="not_required",
            worker_detail="Synchronous mode runs inside the web request. No background worker is needed.",
        )

    if mode == "thread":
        return ProcessingRuntimeStatus(
            mode=mode,
            auto_process_on_upload=auto_process,
            storage_backend=storage_backend,
            storage_shared=storage_shared,
            local_worker_override=local_worker_override,
            broker_configured=broker_configured,
            eager=eager,
            worker_status="not_required",
            worker_detail="Thread mode runs inside the Django process. No Redis or Celery worker is needed.",
        )

    if mode != "celery":
        return ProcessingRuntimeStatus(
            mode=mode,
            auto_process_on_upload=auto_process,
            storage_backend=storage_backend,
            storage_shared=storage_shared,
            local_worker_override=local_worker_override,
            broker_configured=broker_configured,
            eager=eager,
            worker_status="misconfigured",
            worker_detail="Unsupported PROCESSING_MODE. Use sync, thread, or celery.",
        )

    if eager:
        return ProcessingRuntimeStatus(
            mode=mode,
            auto_process_on_upload=auto_process,
            storage_backend=storage_backend,
            storage_shared=storage_shared,
            local_worker_override=local_worker_override,
            broker_configured=broker_configured,
            eager=eager,
            worker_status="eager",
            worker_detail="Celery eager mode is enabled. Tasks execute immediately in-process for local checks.",
        )

    if not storage_shared and not local_worker_override:
        return ProcessingRuntimeStatus(
            mode=mode,
            auto_process_on_upload=auto_process,
            storage_backend=storage_backend,
            storage_shared=storage_shared,
            local_worker_override=local_worker_override,
            broker_configured=broker_configured,
            eager=eager,
            worker_status="misconfigured",
            worker_detail=(
                "Celery worker mode requires shared file storage for real separate services. "
                "Set FILE_STORAGE_BACKEND=s3 for cloud deployment, or set ALLOW_LOCAL_FILE_WORKER=True "
                "only when Django and Celery share the same local filesystem."
            ),
        )

    if not broker_configured:
        return ProcessingRuntimeStatus(
            mode=mode,
            auto_process_on_upload=auto_process,
            storage_backend=storage_backend,
            storage_shared=storage_shared,
            local_worker_override=local_worker_override,
            broker_configured=broker_configured,
            eager=eager,
            worker_status="misconfigured",
            worker_detail="Celery mode is selected, but CELERY_BROKER_URL is empty.",
        )

    return _probe_celery_worker(
        mode=mode,
        auto_process=auto_process,
        storage_backend=storage_backend,
        storage_shared=storage_shared,
        local_worker_override=local_worker_override,
        broker_configured=broker_configured,
        eager=eager,
    )


def _probe_celery_worker(
    *,
    mode: str,
    auto_process: bool,
    storage_backend: str,
    storage_shared: bool,
    local_worker_override: bool,
    broker_configured: bool,
    eager: bool,
) -> ProcessingRuntimeStatus:
    local_note = ""
    if local_worker_override and not storage_shared:
        local_note = " Local filesystem worker override is enabled for same-machine development only."

    try:
        from doc2onec.celery import app as celery_app

        inspect = celery_app.control.inspect(timeout=1.0)
        ping_result = inspect.ping() if inspect else None
    except Exception as exc:
        return ProcessingRuntimeStatus(
            mode=mode,
            auto_process_on_upload=auto_process,
            storage_backend=storage_backend,
            storage_shared=storage_shared,
            local_worker_override=local_worker_override,
            broker_configured=broker_configured,
            eager=eager,
            worker_status="offline",
            worker_detail=f"Celery ping failed: {exc}.{local_note}".strip(),
        )

    if ping_result:
        workers = ", ".join(sorted(ping_result.keys()))
        return ProcessingRuntimeStatus(
            mode=mode,
            auto_process_on_upload=auto_process,
            storage_backend=storage_backend,
            storage_shared=storage_shared,
            local_worker_override=local_worker_override,
            broker_configured=broker_configured,
            eager=eager,
            worker_status="online",
            worker_detail=f"Celery worker responded: {workers}.{local_note}".strip(),
        )

    return ProcessingRuntimeStatus(
        mode=mode,
        auto_process_on_upload=auto_process,
        storage_backend=storage_backend,
        storage_shared=storage_shared,
        local_worker_override=local_worker_override,
        broker_configured=broker_configured,
        eager=eager,
        worker_status="offline",
        worker_detail=f"Broker is configured, but no Celery worker responded to ping.{local_note}".strip(),
    )
