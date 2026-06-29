@echo off
setlocal
set "ROOT=%~dp0"
if exist "%ROOT%.venv\Scripts\pythonw.exe" (
  "%ROOT%.venv\Scripts\pythonw.exe" -m lily.desktop %*
) else if exist "%ROOT%.venv\Scripts\python.exe" (
  "%ROOT%.venv\Scripts\python.exe" -m lily.desktop %*
) else (
  python -m lily.desktop %*
)
endlocal
