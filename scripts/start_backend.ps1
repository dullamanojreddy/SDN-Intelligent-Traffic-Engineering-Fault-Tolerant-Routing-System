# Start FastAPI Backend on Windows
Write-Host "Starting SDN-ITE FastAPI Backend..." -ForegroundColor Cyan

if (Test-Path ".\.venv\Scripts\python.exe") {
    & ".\.venv\Scripts\python.exe" -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
} else {
    python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
}
