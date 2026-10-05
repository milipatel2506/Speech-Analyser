# Start Cadence locally: backend API (port 8000) + dashboard (port 5173), each in its own window.
# Usage (from the project folder):   powershell -ExecutionPolicy Bypass -File .\start.ps1
# Close the two windows to stop the servers.

$root = $PSScriptRoot
# pick up tools installed after this terminal was opened (uv, node, ffmpeg via winget)
$env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')

if (-not (Test-Path "$root\.venv")) {
    Write-Host "First run: installing Python dependencies..." -ForegroundColor Cyan
    Push-Location $root; uv sync; Pop-Location
}
if (-not (Test-Path "$root\frontend\node_modules")) {
    Write-Host "First run: installing dashboard dependencies..." -ForegroundColor Cyan
    Push-Location "$root\frontend"; npm ci; Pop-Location
}

Start-Process powershell -WorkingDirectory $root -ArgumentList @(
    '-NoExit', '-Command',
    "`$host.UI.RawUI.WindowTitle = 'Cadence backend (8000)'; uv run uvicorn speech_analyser.api.main:app --app-dir src --host 127.0.0.1 --port 8000"
)
Start-Process powershell -WorkingDirectory "$root\frontend" -ArgumentList @(
    '-NoExit', '-Command',
    "`$host.UI.RawUI.WindowTitle = 'Cadence dashboard (5173)'; npm run dev -- --host 127.0.0.1 --port 5173"
)

Write-Host "Waiting for the backend..." -ForegroundColor Cyan
for ($i = 0; $i -lt 60; $i++) {
    try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 http://127.0.0.1:8000/api/health | Out-Null; break } catch { Start-Sleep 1 }
}
Start-Process "http://127.0.0.1:5173"
Write-Host "Dashboard: http://127.0.0.1:5173   (close the two server windows to stop)" -ForegroundColor Green
