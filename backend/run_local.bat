@echo off
title GhostSync - Local Test
echo.
echo  ======================================
echo   👻 GhostSync - Local Development
echo  ======================================
echo.

cd /d "%~dp0"

:: Check if venv exists
if exist "venv\Scripts\activate.bat" (
    echo [*] Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo [*] Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo [*] Installing dependencies...
    pip install -r requirements.txt
)

echo.
echo [*] Starting GhostSync GUI...
echo.
python ghostsync_gui.py

pause
