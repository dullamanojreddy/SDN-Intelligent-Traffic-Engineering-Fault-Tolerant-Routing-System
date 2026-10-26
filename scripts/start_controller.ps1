# Start Controller on Windows
Write-Host "Starting SDN-ITE Controller Engine..." -ForegroundColor Cyan

if ((Test-Path ".\.venv\pyvenv.cfg") -and (Test-Path ".\.venv\Scripts\python.exe")) {
    & ".\.venv\Scripts\python.exe" controller/app.py
} else {
    Write-Host "Project .venv is unavailable; using Python 3.10." -ForegroundColor Yellow
    py -3.10 controller/app.py
}
