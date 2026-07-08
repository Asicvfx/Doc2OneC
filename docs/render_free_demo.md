# Render Free Demo Guide

This guide is for a no-card Render deployment path that matches the current MVP as closely as possible.

## What this free profile is for

Use this profile when you want:
- a public demo URL
- no payment method on Render
- the simplest possible cloud deployment for the current Django monolith

Use the file:
- `render.free.yaml`

## What this free profile does

It creates:
- one free Render web service
- one free Render Postgres database
- `PROCESSING_MODE=thread`

It does not create:
- persistent disk
- Redis
- separate worker

## Why this is different from the safer paid profile

Free Render web services do not support persistent disks. That means uploaded files are stored on an ephemeral filesystem and can disappear when the service redeploys, restarts, or spins down.

For our current app, that is acceptable only as a demo deployment, not as durable production hosting.

## Free profile limitations you must expect

1. The app can spin down after idle time.
2. Cold starts can take around a minute.
3. Uploaded files are not durable.
4. Free Postgres is limited and temporary.
5. This is for demo/testing, not production.

## Best use case for this profile

Use it to:
- show the product to someone
- test the public URL
- verify upload -> processing -> review flow
- demo Swagger and dashboard

Do not use it as your real long-term environment.

## How to deploy

1. Push the repository to GitHub.
2. In Render, create a new Blueprint.
3. Point Render to `render.free.yaml` instead of `render.yaml`.
4. Let it create the free web service and free Postgres database.
5. After deploy, open:
   - `/health/`
   - `/api/runtime/processing/`
   - `/api/docs/`

## Expected runtime result

- `/health/` returns OK
- `/api/runtime/processing/` shows `mode: thread`
- dashboard works
- upload works for demo purposes

## Manual smoke test

1. Open the root page.
2. Open `/health/`.
3. Open `/api/runtime/processing/`.
4. Upload `sample_documents/sample_worklog.txt`.
5. Open the document detail page.
6. Confirm the document reaches `Ready for 1C` or `Needs review`.
7. Download JSON or CSV.

## When to stop using this free profile

Move off this profile when you need:
- durable uploads
- separate worker
- Redis queue
- better uptime
- production reliability

At that point, switch to the paid monolith profile in `render.yaml`, and later to shared object storage plus worker mode.
