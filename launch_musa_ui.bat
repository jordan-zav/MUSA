@echo off
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    set "PY=.venv\Scripts\python.exe"
) else (
    set "PY=python"
)

set "PYTHONPATH=%cd%\src"
%PY% -c "from musa import launch_interface; launch_interface()"

if errorlevel 1 (
    echo.
    echo MUSA UI failed to start. Check Python environment and dependencies.
    pause
)

endlocal
