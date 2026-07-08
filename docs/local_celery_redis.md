# Local Redis + Celery Bootstrap

This guide gives two local ways to run Doc2OneC with real Celery background processing.

Important: this guide is for same-machine local development only. It uses `ALLOW_LOCAL_FILE_WORKER=True`, which is acceptable only when Django and Celery share the same local filesystem. For cloud deployment or separate services, use `FILE_STORAGE_BACKEND=s3` instead.

## Option A: No Docker

Use this if you already have Redis installed locally or through WSL.

1. Copy `.env.celery.example` to `.env`
2. Start Redis on `localhost:6379`
3. Start Django:
   ```powershell
   .\.venv\Scripts\python.exe manage.py runserver
   ```
4. Start the worker in another terminal:
   ```powershell
   .\scripts\dev_celery_worker.ps1
   ```
5. Check runtime status:
   ```powershell
   .\scripts\dev_runtime_check.ps1
   ```

Expected result:
- `mode` = `celery`
- `worker_status` = `online`
- `local_worker_override` = `true`

## Option B: Docker only for Redis

Use this if you do not want to install Redis directly on Windows.

1. Copy `.env.celery.example` to `.env`
2. Start Redis with Docker Compose:
   ```powershell
   docker compose -f docker-compose.redis.yml up -d
   ```
3. Confirm Redis container is healthy:
   ```powershell
   docker compose -f docker-compose.redis.yml ps
   ```
4. Start Django:
   ```powershell
   .\.venv\Scripts\python.exe manage.py runserver
   ```
5. Start the worker in another terminal:
   ```powershell
   .\scripts\dev_celery_worker.ps1
   ```
6. Check runtime status:
   ```powershell
   .\scripts\dev_runtime_check.ps1
   ```

Expected result:
- `mode` = `celery`
- `worker_status` = `online`
- `local_worker_override` = `true`

## Manual Smoke Test

1. Open `http://127.0.0.1:8000/`
2. Confirm the dashboard panel says `Mode: celery`
3. Confirm the panel reports worker online
4. Confirm the panel shows `Local worker override`
5. Upload `sample_documents/sample_worklog.txt`
6. Check document status flow:
   - `Queued`
   - `Processing`
   - `Ready for 1C` or `Needs review`
7. Open `http://127.0.0.1:8000/api/runtime/processing/`
8. Confirm the JSON says `worker_status: online`

## Troubleshooting

### Runtime says `misconfigured`
- Check `PROCESSING_MODE=celery`
- Check `CELERY_BROKER_URL`
- Check `CELERY_RESULT_BACKEND`
- Check `ALLOW_LOCAL_FILE_WORKER=True` for same-machine local Celery
- For cloud deployment, do not use the local override; switch to `FILE_STORAGE_BACKEND=s3`

### Runtime says `offline`
- Redis is not running
- Celery worker is not running
- Broker URL points to the wrong host or port

### Runtime says `eager`
- `CELERY_TASK_ALWAYS_EAGER=True`
- This is okay for code-path checks, but it is not real async background processing
