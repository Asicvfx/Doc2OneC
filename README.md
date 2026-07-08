# Doc2OneC

Doc2OneC is a polished Django MVP for processing employee work documents and preparing stable structured data for 1C.

Companies often receive daily work reports from employees or contractors in different formats: TXT, CSV, XLSX, PDF, scanned images, or short free-form text. The same business event can be written in many ways, while 1C needs predictable fields such as employee, date, object, work type, hours, and comment.

## Solution

The platform demonstrates the full internal workflow:

Upload document -> detect file type -> parse/OCR placeholder -> AI-style extraction -> normalized JSON -> backend validation -> status tracking -> JSON/CSV export for 1C -> future 1C adapter placeholder.

This is intentionally a modular monolith: simple enough for an MVP, but organized so real OCR, LLM extraction, object review, and 1C integration can be added without rewriting the product.

## Tech Stack

- Python 3.12 target runtime
- Django
- Django REST Framework
- drf-spectacular for OpenAPI/Swagger documentation
- SQLite for local demo
- PostgreSQL-ready via `DATABASE_URL`
- Django templates
- Bootstrap 5 CDN
- Vanilla JavaScript only through Bootstrap bundle
- `openpyxl` for XLSX parsing
- `pypdf` for text-based PDF extraction
- `PyMuPDF` for rendering scanned PDF pages before OCR
- `django-environ` for environment variables
- `gunicorn` and `whitenoise` for deployment

## MVP Features

- Dashboard with document status metrics
- Document upload for TXT, CSV, XLSX, text-based PDF, scanned PDF OCR, and image OCR
- File type detection
- Text/table/PDF/OCR parsing
- Mock AI-style extraction of worklog fields
- Normalized JSON output
- Directory validation against employees, work objects, and work types
- Processing logs timeline
- Manual review/edit workflow for normalized worklog data
- JSON and CSV export
- Mock 1C adapter class
- Django admin for directories and documents
- DRF API endpoints and Swagger UI
- Demo seed command and sample files

## Architecture

Apps:

- `core`: dashboard and shared product views
- `documents`: document model, upload/list/detail/actions, processing pipeline
- `directories`: employees, work objects, work types, and demo seed command

Service layer:

- `documents/services/file_detector.py`: extension-based file type detection
- `documents/services/file_parser.py`: TXT, CSV, XLSX, text-based PDF parsing, scanned PDF rendering, and image OCR handoff
- `documents/services/ai_extractor.py`: deterministic mock extraction
- `documents/services/ai_provider.py`: environment-selected mock/OpenAI extraction provider
- `documents/services/ocr.py`: OpenAI Vision OCR provider for images and scanned PDFs
- `documents/services/normalizer.py`: stable field cleanup and hours normalization
- `documents/services/validator.py`: required field and directory validation
- `documents/services/exporter.py`: JSON/CSV response generation
- `documents/services/one_c_adapter.py`: future 1C integration boundary
- `documents/services/pipeline.py`: orchestrates processing and writes logs
- `documents/services/processing_jobs.py`: queues processing for the web/API layer and can later be swapped to Celery

Views are intentionally thin. Business logic lives in services so the same pipeline can later be called from Celery, an API endpoint, or a webhook.

## AI Provider Configuration

The local MVP uses a safe deterministic provider by default:

```env
AI_PROVIDER=mock
AI_API_KEY=
AI_MODEL=gpt-5.5
AI_TIMEOUT=30
OCR_PROVIDER=disabled
OCR_MODEL=gpt-5.5
OCR_TIMEOUT=30
OCR_MAX_PDF_PAGES=3
PROCESSING_MODE=thread
```

Available provider values:

- `mock`: deterministic local extractor, no external API key required.
- `openai`: real OpenAI Responses API extraction with structured JSON output.

To test real AI extraction locally, keep your key only in `.env` and set:

```env
AI_PROVIDER=openai
AI_API_KEY=your-local-key
AI_MODEL=gpt-5.5
AI_TIMEOUT=30
OCR_PROVIDER=openai
OCR_MODEL=gpt-5.5
OCR_TIMEOUT=30
OCR_MAX_PDF_PAGES=3
PROCESSING_MODE=thread
```

Do not paste API keys into chat or commit them to git. Automated tests use a fake OpenAI client, so they do not spend API credits.

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

On macOS/Linux, activate the environment with:

```bash
source .venv/bin/activate
```

Open:

- Dashboard: http://127.0.0.1:8000/
- Documents: http://127.0.0.1:8000/documents/
- Admin: http://127.0.0.1:8000/admin/


## API and Swagger

The MVP exposes a small DRF API alongside the template UI:

- Swagger UI: http://127.0.0.1:8000/api/docs/
- OpenAPI schema: http://127.0.0.1:8000/api/schema/
- Documents API: `/api/documents/`
- Directories API: `/api/employees/`, `/api/work-objects/`, `/api/work-types/`

Useful document API actions:

- `POST /api/documents/` with multipart `title` and `file`
- `POST /api/documents/{id}/process/`
- `POST /api/documents/{id}/review/`
- `POST /api/documents/{id}/mark-exported/`

Generate and validate the OpenAPI schema locally:

```bash
python manage.py spectacular --file schema.yml --validate
```

## Testing

Run the automated checks before sending the demo:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

## Demo Workflow

1. Run `python manage.py seed_demo_data`.
2. Open `/documents/upload/`.
3. Upload `sample_documents/sample_worklog.txt`, `.csv`, or generated `.xlsx`.
4. Open the document detail page.
5. Click `Run processing`.
6. If the document shows `Processing queued`, wait a few seconds; the detail page auto-refreshes while processing is active.
7. Review extracted text, normalized JSON, validation status, and processing logs.
8. Use `Review / Edit data` if fields need manual correction.
9. Download JSON or CSV.
10. Mark the document as exported.

## Sample Data

The seed command creates:

Employees:

- Иванов Иван
- Петров Сергей
- Сидоров Алексей

Work objects:

- Объект №1
- Объект №2
- Астана-1

Work types:

- Электромонтажные работы
- Монтаж кабеля
- Техническое обслуживание

It also creates `sample_documents/sample_worklog.xlsx` when `openpyxl` is installed.

## Deployment Notes

The project includes Render/Railway-friendly files:

- `Procfile`
- `runtime.txt`
- `requirements.txt`
- `.env.example`
- `whitenoise` static file support
- `gunicorn` WSGI entrypoint
- `DATABASE_URL` support for PostgreSQL

Typical production variables:

```env
SECRET_KEY=change-me
DEBUG=False
ALLOWED_HOSTS=your-domain.com,your-app.onrender.com
DATABASE_URL=postgres://...
AI_PROVIDER=mock
AI_API_KEY=
ONE_C_BASE_URL=
ONE_C_USERNAME=
ONE_C_PASSWORD=
```

Run `python manage.py collectstatic --noinput` during deployment.

## Future Improvements

- Real OCR for images and scanned PDFs
- Real LLM extraction with structured outputs and prompt versioning
- 1C OData/API integration after endpoint and credential discovery
- Accounting review and correction flow
- Role-based access control
- API keys for machine-to-machine ingestion
- S3 or MinIO file storage
- Replace MVP thread processing with Celery/Redis for production-scale large files
- Audit log and retention policy for production use
