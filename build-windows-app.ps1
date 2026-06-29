$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Project venv not found. Create it first, then run: pip install -r requirements.txt"
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
    "lily\desktop.py"

Write-Host "Built: $root\dist\Lily\Lily.exe"
