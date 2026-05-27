# River Sentinel - Backend Startup Script

Write-Host "Starting River Sentinel Backend..." -ForegroundColor Cyan

# Navigate to backend directory
Set-Location -Path $PSScriptRoot\backend

# Check if virtual environment exists
if (-Not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
.\venv\Scripts\Activate.ps1

# Install/update dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt --quiet

# Start Flask server
Write-Host "`n Starting Flask API on http://localhost:5000" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop the server`n" -ForegroundColor Gray
python app.py
