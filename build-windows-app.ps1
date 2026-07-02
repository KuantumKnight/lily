$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Project venv not found. Create it first, then run: pip install -r requirements.txt"
}

Write-Host "Running smoke checks"
& $python (Join-Path $root "scripts\smoke_check.py")

$exe = Join-Path $root "dist\Lily\Lily.exe"
if (Test-Path $exe) {
    Get-CimInstance Win32_Process |
        Where-Object { $_.ExecutablePath -eq $exe } |
        ForEach-Object {
            Write-Host "Stopping running Lily.exe (PID $($_.ProcessId)) before rebuild"
            Stop-Process -Id $_.ProcessId -Force
        }
}

& $python -m pip install pyinstaller
& $python -m PyInstaller `
    --noconfirm `
    --windowed `
    --name Lily `
    --add-data "lily\dashboard_static;lily\dashboard_static" `
    --hidden-import "uvicorn.loops.auto" `
    --hidden-import "uvicorn.protocols.http.auto" `
    --hidden-import "uvicorn.protocols.websockets.wsproto_impl" `
    --hidden-import "fastapi" `
    --hidden-import "starlette" `
    --collect-submodules "lily" `
    "lily_desktop.py"

Write-Host "Built: $root\dist\Lily\Lily.exe"
