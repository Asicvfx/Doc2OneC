$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    throw "Virtual environment not found. Create it first with: python -m venv .venv"
}

& .\.venv\Scripts\python.exe manage.py check_processing_runtime