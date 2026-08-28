# Stop all processes on Windows
Write-Host "Stopping all running python and node processes for SDN-ITE..." -ForegroundColor Yellow
Get-Process -Name "python", "node", "uvicorn" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Write-Host "Processes stopped." -ForegroundColor Green
