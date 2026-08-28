# Start Controller on Windows
Write-Host "Starting SDN-ITE Controller Engine..." -ForegroundColor Cyan

if (Test-Path ".\.venv\Scripts\python.exe") {
    & ".\.venv\Scripts\python.exe" controller/app.py
} else {
    python controller/app.py
}
