$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPythonw = Join-Path $root ".venv\Scripts\pythonw.exe"
$venvPython = Join-Path $root ".venv\Scripts\python.exe"

if (Test-Path $venvPythonw) {
    & $venvPythonw -m lily.desktop @args
    exit $LASTEXITCODE
}

if (Test-Path $venvPython) {
    & $venvPython -m lily.desktop @args
    exit $LASTEXITCODE
}

python -m lily.desktop @args
