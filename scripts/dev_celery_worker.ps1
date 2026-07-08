$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    throw "Virtual environment not found. Create it first with: python -m venv .venv"
}

& .\.venv\Scripts\celery.exe -A doc2onec worker -l info