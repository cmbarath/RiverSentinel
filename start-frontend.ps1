# River Sentinel - Frontend Startup Script

Write-Host "Starting River Sentinel Frontend..." -ForegroundColor Cyan

# Navigate to frontend directory
Set-Location -Path $PSScriptRoot\frontend

# Check if node_modules exists
if (-Not (Test-Path "node_modules")) {
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    npm install
}

# Start Next.js dev server
Write-Host "`n Starting Next.js on http://localhost:3000" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop the server`n" -ForegroundColor Gray
npm run dev
