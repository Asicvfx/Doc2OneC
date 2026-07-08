# Doc2OneC

Doc2OneC is a Django MVP for processing employee worklog documents and preparing stable structured data for 1C.

Companies often receive daily work reports in TXT, CSV, XLSX, PDF, scanned PDF, image, or free-form text form. The same work event can be written many different ways, while 1C expects predictable fields such as employee, date, object, work type, hours, and comment.

## Solution

The platform demonstrates the full internal workflow:

Upload document -> detect file type -> parse/OCR -> AI extraction -> normalized JSON -> backend validation -> status tracking -> manual review if needed -> JSON/CSV export -> future 1C adapter boundary.

The codebase is a modular monolith: small enough for an MVP, but structured so real OCR, LLM extraction, human review, background workers, and 1C integration can evolve without a rewrite.

## Tech Stack

- Python 3.12 target runtime
- Django 5
- Django REST Framework
- drf-spectacular for OpenAPI/Swagger docs
- SQLite for local demo
- PostgreSQL-ready via `DATABASE_URL`
- Django templates + Bootstrap 5
- `openpyxl` for XLSX parsing
- `pypdf` for text-based PDF extraction
- `PyMuPDF` for scanned PDF rendering before OCR
- `openai` for optional AI extraction and OCR
- `celery[redis]` for production-ready background processing
- `gunicorn` + `whitenoise` for deployment

## MVP Features

- Dashboard with live processing visibility
- Document upload for TXT, CSV, XLSX, PDF, PNG, JPG, JPEG
- File type detection
- Text, table, PDF, and OCR parsing
- Mock and OpenAI-based extraction providers
- Normalized JSON output
- Directory validation against employees, work objects, and work types
- Manual review/edit workflow
- JSON and CSV export
- Mock 1C adapter boundary
- Django admin for documents and directories
- DRF API + Swagger UI
- Demo seed command and sample files
- Processing modes: `sync`, `thread`, `celery`

## Architecture

Apps:

- `core`: dashboard and shared product pages
- `documents`: document model, UI, API, processing flow, review, export, Celery task
- `directories`: employees, work objects, work types, demo seed command

Service layer:

- `documents/services/file_detector.py`: extension-based type detection
- `documents/services/file_parser.py`: TXT, CSV, XLSX, PDF, image parsing and OCR handoff
- `documents/services/ai_provider.py`: mock/OpenAI extraction provider selection
- `documents/services/ocr.py`: OCR provider selection and OpenAI Vision OCR
- `documents/services/normalizer.py`: stable field cleanup and hours normalization
- `documents/services/validator.py`: backend validation rules
- `documents/services/manual_review.py`: review save + revalidation flow
- `documents/services/exporter.py`: JSON/CSV exports
- `documents/services/export_status.py`: export readiness rules
- `documents/services/pipeline.py`: main processing pipeline
- `documents/services/processing_jobs.py`: queue/start processing for web, API, thread mode, and Celery mode
- `documents/services/processing_status.py`: user-facing processing issue summaries
- `documents/services/one_c_adapter.py`: future 1C integration boundary
- `documents/tasks.py`: Celery background task entrypoint

Views stay thin. Business rules live in services so the same flow can be called from web UI, API, thread mode, and a future worker fleet.

## Environment

Local default example:

```env
SECRET_KEY=
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=
SECURE_SSL_REDIRECT=False
SECURE_HSTS_SECONDS=0
SECURE_HSTS_INCLUDE_SUBDOMAINS=False
SECURE_HSTS_PRELOAD=False
DATABASE_URL=
AI_PROVIDER=mock
AI_API_KEY=
AI_MODEL=gpt-5.5
AI_TIMEOUT=30
OCR_PROVIDER=disabled
OCR_MODEL=gpt-5.5
OCR_TIMEOUT=30
OCR_MAX_PDF_PAGES=3
PROCESSING_MODE=thread
CELERY_BROKER_URL=
CELERY_RESULT_BACKEND=
CELERY_TASK_ALWAYS_EAGER=False
CELERY_TASK_EAGER_PROPAGATES=True
AUTO_PROCESS_ON_UPLOAD=true
ONE_C_BASE_URL=
ONE_C_USERNAME=
ONE_C_PASSWORD=
```

Provider notes:

- `AI_PROVIDER=mock`: deterministic local extractor, no external API key required
- `AI_PROVIDER=openai`: real OpenAI extraction
- `OCR_PROVIDER=disabled`: skip OCR for images/scanned PDFs
- `OCR_PROVIDER=openai`: use OpenAI Vision OCR

Processing mode notes:

- `PROCESSING_MODE=sync`: easiest for debugging, runs inside the request
- `PROCESSING_MODE=thread`: best local demo default, no Redis required
- `PROCESSING_MODE=celery`: production-ready worker mode

Celery notes:

- `CELERY_BROKER_URL=redis://localhost:6379/0`
- `CELERY_RESULT_BACKEND=redis://localhost:6379/0`
- `CELERY_TASK_ALWAYS_EAGER=True` can be used for local code-path checks without Redis, but it is not real background processing

Keep API keys only in `.env`. Do not commit them.

## Local Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py seed_demo_data
python manage.py createsuperuser
python manage.py runserver
```

macOS/Linux activation:

```bash
source .venv/bin/activate
```

Open locally:

- Dashboard: http://127.0.0.1:8000/
- Documents: http://127.0.0.1:8000/documents/
- Admin: http://127.0.0.1:8000/admin/
- Swagger UI: http://127.0.0.1:8000/api/docs/
- OpenAPI schema: http://127.0.0.1:8000/api/schema/

## Local Celery Bootstrap Files

Useful files for local Redis + Celery setup:

- `.env.celery.example`
- `docker-compose.redis.yml`
- `scripts/dev_celery_worker.ps1`
- `scripts/dev_runtime_check.ps1`
- `docs/local_celery_redis.md`
## Running Modes

### Mode 1: Simple local demo

Use this when you just want the app to work locally without extra services.

```env
PROCESSING_MODE=thread
AUTO_PROCESS_ON_UPLOAD=true
```

Start only Django:

```bash
python manage.py runserver
```

### Smoke check for runtime status

Once the app is running, you can verify the processing backend in two ways:

1. Browser/API check:
   - Open `http://127.0.0.1:8000/api/runtime/processing/`
   - In `thread` mode you should see `worker_status: not_required`
   - In `celery` mode with a live worker you should see `worker_status: online`

2. CLI check:

```bash
python manage.py check_processing_runtime
```

This prints JSON with the current mode, broker configuration, eager flag, and worker visibility.
### Mode 2: Real Celery worker locally

Use this when you want to test the production-style background path.

Set in `.env`:

```env
PROCESSING_MODE=celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
AUTO_PROCESS_ON_UPLOAD=true
```

Start Redis, then run these in separate terminals:

```bash
python manage.py runserver
celery -A doc2onec worker -l info
```

If you do not want Docker, install Redis directly on your machine or run it through WSL. Docker is optional, not required by the project. A complete Windows-friendly step-by-step guide is in `docs/local_celery_redis.md`.

### Mode 3: Celery code-path check without Redis

This is useful only for quick local checks.

```env
PROCESSING_MODE=celery
CELERY_TASK_ALWAYS_EAGER=True
AUTO_PROCESS_ON_UPLOAD=true
```

In this mode, Celery tasks execute immediately in-process.

## API

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

## Checks

Run these before demoing or deploying:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py spectacular --file schema.yml --validate
python manage.py test
python manage.py collectstatic --noinput
```

## Demo Workflow

1. Run `python manage.py seed_demo_data`.
2. Open `/documents/upload/`.
3. Upload `sample_documents/sample_worklog.txt`, `.csv`, or `.xlsx`.
4. The document is queued automatically when `AUTO_PROCESS_ON_UPLOAD=true`.
5. Open the detail page if it does not open automatically.
6. If the document shows `Queued` or `Processing`, wait a few seconds. The detail page, dashboard, and document list auto-refresh while active processing exists.
7. Review extracted text, normalized JSON, validation status, and processing logs.
8. If the status is `Needs review`, open `Review / Edit data`, fix the fields, and save.
9. Download JSON or CSV.
10. Mark the document as exported.

## Sample Data

The seed command creates:

Employees:

- Ivanov Ivan
- Petrov Sergey
- Sidorov Aleksei

Work objects:

- Object No. 1
- Object No. 2
- Astana-1

Work types:

- Electrical installation work
- Cable installation
- Technical maintenance

It also refreshes the sample files in `sample_documents/`.

## Render Deployment Notes

The current safest Render deployment is a single Django web service with Postgres and a persistent disk, using `PROCESSING_MODE=thread`.

Why: Render persistent disks are attached to a single service, so the current local-file upload flow is not yet safe for a separate Celery worker. A full web + worker Render architecture becomes correct after the future shared-storage stage.

Detailed guide: `docs/render_deploy.md`

## Deployment Notes

Included deploy-friendly files:

- `Procfile`
- `runtime.txt`
- `requirements.txt`
- `.env.example`

Recommended production variables:

```env
SECRET_KEY=change-me
DEBUG=False
ALLOWED_HOSTS=your-domain.com,your-app.onrender.com
CSRF_TRUSTED_ORIGINS=https://your-domain.com,https://your-app.onrender.com
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=3600
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
DATABASE_URL=postgres://...
AI_PROVIDER=mock
AI_API_KEY=
OCR_PROVIDER=disabled
PROCESSING_MODE=celery
CELERY_BROKER_URL=redis://...
CELERY_RESULT_BACKEND=redis://...
AUTO_PROCESS_ON_UPLOAD=true
ONE_C_BASE_URL=
ONE_C_USERNAME=
ONE_C_PASSWORD=
```

Deployment commands:

- Release: `python manage.py migrate --noinput`
- Web: `gunicorn doc2onec.wsgi:application`
- Worker: `celery -A doc2onec worker -l info`
- Static: `python manage.py collectstatic --noinput`

## Future Stages

- Add shared object storage for uploads, then switch Render deploys to web + worker + Key Value
- Add true 1C OData/API integration
- Add richer review guidance and field suggestions
- Add authentication/roles for production use
- Add S3/MinIO media storage
- Add audit logging and retention policy
- Add machine-to-machine ingestion API keys