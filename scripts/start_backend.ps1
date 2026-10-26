# Start FastAPI Backend on Windows
Write-Host "Starting SDN-ITE FastAPI Backend..." -ForegroundColor Cyan

if ((Test-Path ".\.venv\pyvenv.cfg") -and (Test-Path ".\.venv\Scripts\python.exe")) {
    & ".\.venv\Scripts\python.exe" -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
} else {
    Write-Host "Project .venv is unavailable; using Python 3.10." -ForegroundColor Yellow
    py -3.10 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
}
