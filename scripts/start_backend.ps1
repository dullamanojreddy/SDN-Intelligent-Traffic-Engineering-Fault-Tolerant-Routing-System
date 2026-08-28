# Start FastAPI Backend on Windows
Write-Host "Starting SDN-ITE FastAPI Backend..." -ForegroundColor Cyan
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
