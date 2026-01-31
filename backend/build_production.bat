@echo off
title GhostSync - Production Build
echo.
echo  ======================================================
echo   GHOSTSYNC PRODUCTION BUILD
echo  ======================================================
echo.

cd /d "%~dp0"

:: Check for venv
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found!
    echo Run: python -m venv venv
    pause
    exit /b 1
)

:: Activate venv
call venv\Scripts\activate.bat

:: Install build dependencies
echo [1/4] Installing build dependencies...
pip install pyinstaller pyinstaller-hooks-contrib -q

:: Clean previous builds
echo [2/4] Cleaning previous builds...
if exist "dist" rmdir /s /q dist
if exist "build" rmdir /s /q build

:: Verify cloudflared exists
if not exist "cloudflared.exe" (
    echo [!] Downloading cloudflared.exe...
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe' -OutFile 'cloudflared.exe'"
)

:: Build the executable
echo [3/4] Building GhostSync.exe...
pyinstaller GhostSync.spec --noconfirm

:: Check result
if exist "dist\GhostSync.exe" (
    echo.
    echo  ======================================================
    echo   BUILD SUCCESSFUL!
    echo  ======================================================
    echo.
    echo   Output: dist\GhostSync.exe
    echo   Size: 
    for %%A in (dist\GhostSync.exe) do echo          %%~zA bytes
    echo.
    echo   Ready to distribute!
    echo.
) else (
    echo.
    echo  [ERROR] Build failed! Check output above.
    echo.
)

pause
