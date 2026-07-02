$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $root ".venv\Scripts\python.exe"

if (Test-Path $venvPython) {
    & $venvPython (Join-Path $root "scripts\smoke_check.py")
} else {
    & python (Join-Path $root "scripts\smoke_check.py")
}
