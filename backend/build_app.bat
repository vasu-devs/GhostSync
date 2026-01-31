@echo off
echo ==================================================
echo   GhostSync Ultimate - Builder
echo ==================================================
echo.

echo 1. Cleaning previous builds...
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
del /q *.spec 2>nul

echo.
echo 2. Building Executable (With Forced Imports)...
echo.

rem Build command with ALL safety flags
rem --clean: clear pyinstaller cache
rem --collect-all: grab all assets for ctk
rem --hidden-import: force python to see the module

if exist "cloudflared.exe" (
    pyinstaller --noconsole --onefile --clean ^
    --name "GhostSync_Ultimate" ^
    --splash splash.png ^
    --collect-all customtkinter ^
    --hidden-import customtkinter ^
    --hidden-import PIL ^
    --hidden-import telegram ^
    --add-data "cloudflared.exe;." ^
    ghostsync_gui.py
) else (
    echo WARNING: cloudflared.exe not found.
    pyinstaller --noconsole --onefile --clean ^
    --name "GhostSync_Ultimate" ^
    --splash splash.png ^
    --collect-all customtkinter ^
    --hidden-import customtkinter ^
    --hidden-import PIL ^
    --hidden-import telegram ^
    ghostsync_gui.py
)

echo.
echo ==================================================
echo   BUILD COMPLETE!
echo ==================================================
echo.
echo Your file: dist\GhostSync_Ultimate.exe
echo.
pause
