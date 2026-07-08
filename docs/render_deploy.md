# Render Deployment Guide

This project is currently safest on Render as a single Django web service with Postgres and a persistent disk for uploaded files.

## Why the current Render-safe mode uses thread processing

The application stores uploaded files in `MEDIA_ROOT` and the processing pipeline reads those files later.

Render persistent disks are attached to a single service and are not shared with other services. That means a separate Celery worker cannot safely read files written by the web service unless uploads live in shared object storage such as S3.

Because of that, the current deployment recommendation is:

- Web service on Render
- Render Postgres
- Persistent disk mounted to the web service
- `PROCESSING_MODE=thread`

This keeps upload and processing on the same service instance.

## Files added for Render

- `render.yaml`
- `.env.render.example`
- `build.sh`
- `/health/` endpoint

## Recommended Render setup now

1. Push the repository to GitHub
2. In Render, create a new Blueprint from the repository
3. Let Render read `render.yaml`
4. Confirm the web service and Postgres database are created
5. After the first deploy, open:
   - `/health/`
   - `/api/runtime/processing/`
   - `/api/docs/`

Expected runtime result:
- `/health/` returns `{ "status": "ok", "database": "up" }`
- `/api/runtime/processing/` returns `mode: thread`

## Environment notes

The settings automatically add `RENDER_EXTERNAL_HOSTNAME` to:
- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`

So the default Render hostname works without manual host juggling.

## Manual post-deploy smoke test

1. Open the app root page
2. Confirm dashboard loads
3. Open `/health/`
4. Open `/api/runtime/processing/`
5. Confirm it shows `mode: thread`
6. Upload `sample_documents/sample_worklog.txt`
7. Open the created document
8. Confirm status moves through processing and finishes as `Ready for 1C` or `Needs review`
9. Download JSON or CSV

## Important limitation right now

Do not deploy the current project on Render with both:
- `PROCESSING_MODE=celery`
- file uploads stored on the web service disk

That combination is not safe because the worker service cannot access the same persistent disk.

## What unlocks worker mode

The project now supports shared object storage for uploads. To run web + worker correctly on Render, use:

- `FILE_STORAGE_BACKEND=s3`
- object storage such as AWS S3, Cloudflare R2, Backblaze B2 via S3 API, or another S3-compatible provider
- Render web service
- Render background worker
- Render Key Value or another Redis-compatible broker
- Render Postgres

## Render-safe MVP vs later architecture

### Safe now
- Render web
- Render Postgres
- Persistent disk
- `PROCESSING_MODE=thread`

### Later
- Render web
- Render worker
- Render Key Value
- Render Postgres
- shared object storage for uploads

