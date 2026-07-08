# Doc2OneC

Doc2OneC is a Django demo platform for processing employee worklog documents and preparing stable structured data for 1C.

It accepts messy source files such as TXT, CSV, XLSX, PDF, scanned PDF, and images, extracts worklog fields, validates them against directories, and sends the operator through review before export.

## What the demo shows

The product flow is:

Upload -> detect file type -> parse or OCR -> AI extraction -> normalize JSON -> validate -> review if needed -> export JSON or CSV -> mark exported.

This repository is a modular monolith. The codebase is still MVP-sized, but the service boundaries are already separated so OCR, OpenAI extraction, Celery workers, S3 storage, and 1C integration can evolve without a rewrite.

## Tech stack

- Python 3.12
- Django 5
- Django REST Framework
- drf-spectacular for OpenAPI and Swagger
- SQLite for local demo
- PostgreSQL via `DATABASE_URL`
- Django templates and Bootstrap 5 (stored in `frontend/`)
- `openpyxl` for XLSX parsing
- `pypdf` for text PDFs
- `PyMuPDF` for scanned PDF rendering before OCR
- `openai` for optional extraction and OCR
- `celery[redis]` for production-style background processing
- `gunicorn` and `whitenoise` for deployment

## Main features

- Internal dashboard with runtime visibility
- Upload flow for TXT, CSV, XLSX, PDF, PNG, JPG, JPEG
- File type detection and parsing
- OCR path for images and scanned PDFs
- Mock and OpenAI extraction providers
- Normalized JSON output
- Backend validation against employees, work objects, and work types
- Manual review and correction workflow
- JSON and CSV export
- 1C adapter boundary for future integration
- Django admin, API, and Swagger UI
- Local demo seed command and sample files
- Processing modes: `sync`, `thread`, `celery`

## Project structure

- `backend/` - Django apps, settings, `manage.py`, and Python dependencies
- `frontend/` - templates and static assets
- `docs/` - setup and deployment guides

Django apps:

- `core` - dashboard, healthcheck, shared views
- `documents` - model, web UI, API, processing flow, review, export, Celery entrypoint
- `directories` - employees, work objects, work types, demo seed command

Important services:

- `documents/services/file_detector.py`
- `documents/services/file_parser.py`
- `documents/services/ocr.py`
- `documents/services/ai_provider.py`
- `documents/services/normalizer.py`
- `documents/services/validator.py`
- `documents/services/manual_review.py`
- `documents/services/exporter.py`
- `documents/services/export_status.py`
- `documents/services/pipeline.py`
- `documents/services/processing_jobs.py`
- `documents/services/processing_status.py`
- `documents/services/one_c_adapter.py`

Views stay thin. Business logic lives in services so the same flow can be reused by web UI, API, thread mode, and Celery mode.

## Environment files

Main example files in the repo:

- `.env.example` - default local setup
- `.env.celery.example` - local Redis plus Celery setup
- `.env.s3.example` - shared object storage plus Celery-safe setup
- `.env.render.example` - single-service Render-style setup

Base variables:

```env
SECRET_KEY=
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=
DATABASE_URL=
MEDIA_ROOT=
FILE_STORAGE_BACKEND=filesystem
AI_PROVIDER=mock
AI_API_KEY=
AI_MODEL=gpt-5.5
AI_TIMEOUT=30
OCR_PROVIDER=disabled
OCR_MODEL=gpt-5.5
OCR_TIMEOUT=30
OCR_MAX_PDF_PAGES=3
PROCESSING_MODE=thread
ALLOW_LOCAL_FILE_WORKER=False
CELERY_BROKER_URL=
CELERY_RESULT_BACKEND=
AUTO_PROCESS_ON_UPLOAD=true
ONE_C_BASE_URL=
ONE_C_USERNAME=
ONE_C_PASSWORD=
```

Provider notes:

- `AI_PROVIDER=mock` - deterministic local extractor, no API key required
- `AI_PROVIDER=openai` - real OpenAI extraction
- `OCR_PROVIDER=disabled` - skip OCR
- `OCR_PROVIDER=openai` - use OpenAI Vision OCR

Processing mode notes:

- `PROCESSING_MODE=sync` - easiest for debugging
- `PROCESSING_MODE=thread` - best local demo default, no Redis required
- `PROCESSING_MODE=celery` - production-style worker mode

## Quick start

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r backend/requirements.txt
copy .env.example .env
python backend/manage.py migrate
python backend/manage.py seed_demo_data
python backend/manage.py runserver
```

macOS or Linux:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env
python backend/manage.py migrate
python backend/manage.py seed_demo_data
python backend/manage.py runserver
```

Useful local URLs:

- Dashboard: `http://127.0.0.1:8000/`
- Documents: `http://127.0.0.1:8000/documents/`
- Admin: `http://127.0.0.1:8000/admin/`
- Swagger UI: `http://127.0.0.1:8000/api/docs/`
- OpenAPI schema: `http://127.0.0.1:8000/api/schema/`
- Healthcheck: `http://127.0.0.1:8000/health/`
- Runtime status: `http://127.0.0.1:8000/api/runtime/processing/`

## How to test the demo manually

### Stage 1: basic smoke test

1. Open `/health/` and confirm it returns OK.
2. Open `/api/runtime/processing/` and confirm the mode is what you expect.
3. Open `/api/docs/` and confirm Swagger loads.

### Stage 2: upload and processing flow

1. Open `/documents/upload/`.
2. Upload one of these files:
   - `sample_documents/sample_worklog.txt`
   - `sample_documents/sample_worklog.csv`
   - `sample_documents/sample_worklog.xlsx`
3. If `AUTO_PROCESS_ON_UPLOAD=true`, the document starts automatically.
4. If auto-process is off, open the document detail page and click `Run processing`.
5. Wait a few seconds if the status is `Queued` or `Processing`.

### Stage 3: review and export

1. Open the document detail page.
2. Check these blocks:
   - `Extracted text`
   - `Normalized JSON`
   - `Validation`
   - `Processing logs`
3. If the document is `Needs review`, click `Review / Edit data`.
4. Fix the fields and save.
5. Download JSON and CSV.
6. Click `Mark as exported`.

### Stage 4: Swagger hand test

1. Open `http://127.0.0.1:8000/api/docs/`.
2. Expand `POST /api/documents/`.
3. Click `Try it out`.
4. Upload a file with `title` and `file`.
5. Execute the request.
6. Copy the returned `id`.
7. Expand `POST /api/documents/{id}/process/` and run it for that id if needed.
8. Expand `GET /api/documents/{id}/` to inspect current status and payload.

## Local runtime modes

### Mode 1: simple local demo

Use this for the easiest local run.

```env
PROCESSING_MODE=thread
ALLOW_LOCAL_FILE_WORKER=False
AUTO_PROCESS_ON_UPLOAD=true
```

Run only Django:

```bash
python backend/manage.py runserver
```

### Mode 2: real Celery worker

Use this when you want a real worker path.

Same-machine local setup:

```env
FILE_STORAGE_BACKEND=filesystem
ALLOW_LOCAL_FILE_WORKER=True
PROCESSING_MODE=celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
AUTO_PROCESS_ON_UPLOAD=true
```

Cloud-safe separate-service setup:

```env
FILE_STORAGE_BACKEND=s3
ALLOW_LOCAL_FILE_WORKER=False
PROCESSING_MODE=celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
AUTO_PROCESS_ON_UPLOAD=true
```

Then run Django and the worker in separate terminals:

```bash
python backend/manage.py runserver
celery --workdir backend -A doc2onec worker -l info
```

Windows helper files:

- `docker-compose.redis.yml`
- `scripts/dev_celery_worker.ps1`
- `scripts/dev_runtime_check.ps1`
- `docs/local_celery_redis.md`

### Mode 3: Celery code-path check without Redis

```env
PROCESSING_MODE=celery
CELERY_TASK_ALWAYS_EAGER=True
AUTO_PROCESS_ON_UPLOAD=true
```

This is useful only for quick code-path checks. It is not real background processing.

## Runtime health checks

Browser or API checks:

- `/health/`
- `/api/runtime/processing/`

CLI check:

```bash
python backend/manage.py check_processing_runtime
```

In `thread` mode you should usually see `worker_status: not_required`.
In `celery` mode with a live worker you should see `worker_status: online`.

## API summary

Main endpoints:

- `POST /api/documents/`
- `GET /api/documents/`
- `GET /api/documents/{id}/`
- `POST /api/documents/{id}/process/`
- `POST /api/documents/{id}/review/`
- `POST /api/documents/{id}/mark-exported/`
- `GET /api/employees/`
- `GET /api/work-objects/`
- `GET /api/work-types/`

## Shared storage

Storage modes:

- `filesystem` - local/default mode
- `s3` - shared object storage for cloud-safe uploads

See:

- `docs/shared_storage.md`
- `.env.s3.example`

Use `FILE_STORAGE_BACKEND=s3` when web and worker are separate services.

## Render deployment

This repo includes two Render profiles:

- `render.free.yaml` - free public demo path, no persistent disk
- `render.yaml` - safer single-service path with persistent disk

Recommended current Render setup:

- one Django web service
- one Postgres database
- persistent disk
- `PROCESSING_MODE=thread`

Why: Render persistent disks are attached to one service only. If you want a separate Celery worker, move uploads to shared object storage first.

Detailed guides:

- `docs/render_free_demo.md`
- `docs/render_deploy.md`

## Deployment files

Included deploy-friendly files:

- `Procfile`
- `runtime.txt`
- `backend/requirements.txt`
- `build.sh`
- `render.yaml`
- `render.free.yaml`

Process commands:

- Release: `python backend/manage.py migrate --noinput`
- Web: `gunicorn --chdir backend doc2onec.wsgi:application`
- Worker: `celery --workdir backend -A doc2onec worker -l info`
- Static: `python backend/manage.py collectstatic --noinput`

## Verification commands

Run these before demoing or deploying:

```bash
python backend/manage.py check
python backend/manage.py makemigrations --check --dry-run
python backend/manage.py spectacular --file schema.yml --validate
python backend/manage.py test
python backend/manage.py collectstatic --noinput
```

## Demo data

`python backend/manage.py seed_demo_data` creates demo employees, work objects, work types, and refreshes files in `sample_documents/`.

## Next production stages

- real 1C OData or API integration
- authentication and roles
- audit logging
- retry policies and queue split
- richer review suggestions
- machine-to-machine ingestion keys




