# Shared Storage Guide

This project now supports two upload storage modes.

## Mode 1: Local filesystem

Use this for local development and the simplest demos.

```env
FILE_STORAGE_BACKEND=filesystem
MEDIA_ROOT=
```

Behavior:
- uploaded files are stored in local `MEDIA_ROOT`
- no cloud object storage is required
- best for local work and simple single-service demos

## Mode 2: S3-compatible storage

Use this when you need shared upload access across web and worker processes.

```env
FILE_STORAGE_BACKEND=s3
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_STORAGE_BUCKET_NAME=...
AWS_S3_REGION_NAME=...
AWS_S3_ENDPOINT_URL=...
AWS_S3_CUSTOM_DOMAIN=
AWS_DEFAULT_ACL=
AWS_QUERYSTRING_AUTH=True
AWS_S3_FILE_OVERWRITE=False
AWS_LOCATION=documents
AWS_S3_ADDRESSING_STYLE=
AWS_S3_URL_PROTOCOL=https:
AWS_S3_OBJECT_PARAMETERS={"CacheControl":"max-age=86400"}
```

Behavior:
- uploaded files are stored in an S3-compatible bucket
- both web and worker can read the same uploaded files
- this unlocks a safe future web + worker deployment model

## Supported providers

Because the backend is S3-compatible, you can use:
- AWS S3
- Cloudflare R2
- Backblaze B2 via S3 API
- MinIO

## Important settings

- `FILE_STORAGE_BACKEND`: `filesystem` or `s3`
- `AWS_STORAGE_BUCKET_NAME`: required for S3 mode
- `AWS_S3_ENDPOINT_URL`: required for non-AWS providers such as R2 or MinIO
- `AWS_QUERYSTRING_AUTH`: set to `False` for public buckets, keep `True` for private buckets
- `AWS_S3_FILE_OVERWRITE`: keep `False` to avoid name collisions
- `AWS_LOCATION`: optional prefix within the bucket
- `AWS_S3_OBJECT_PARAMETERS`: JSON object for shared upload parameters

## Local test plan for S3 mode

1. Copy `.env.s3.example` into `.env`
2. Fill in bucket credentials and endpoint values
3. Run:
   ```powershell
   .\.venv\Scripts\python.exe manage.py check
   .\.venv\Scripts\python.exe manage.py runserver
   ```
4. Upload a sample document
5. Confirm the uploaded document still processes
6. Confirm the document detail page shows a working file URL

## Why this stage matters

This stage removes the biggest architecture blocker for separate workers and cloud-safe uploads.

Before this stage:
- uploads were tied to local disk
- multi-service deploys were fragile

After this stage:
- uploads can live in shared object storage
- future worker mode becomes safe to implement