# GhostSync - Local Development Runner
# Run with: .\run_local.ps1

Write-Host ""
Write-Host " ======================================" -ForegroundColor Cyan
Write-Host "   👻 GhostSync - Local Development" -ForegroundColor White
Write-Host " ======================================" -ForegroundColor Cyan
Write-Host ""

Set-Location $PSScriptRoot

# Check if venv exists
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "[*] Activating virtual environment..." -ForegroundColor Yellow
    & ".\venv\Scripts\Activate.ps1"
} else {
    Write-Host "[*] Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    & ".\venv\Scripts\Activate.ps1"
    Write-Host "[*] Installing dependencies..." -ForegroundColor Yellow
    pip install -r requirements.txt
}

Write-Host ""
Write-Host "[*] Starting GhostSync GUI..." -ForegroundColor Green
Write-Host ""

python ghostsync_gui.py
