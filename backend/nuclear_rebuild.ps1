# nuclear_rebuild.ps1 - The "Fix It Once" Script

# 1. CLEANUP
Write-Host "1. NUKING old builds..." -ForegroundColor Red
if (Test-Path "venv_nuclear") { Remove-Item -Recurse -Force "venv_nuclear" }
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist_nuclear") { Remove-Item -Recurse -Force "dist_nuclear" }
if (Test-Path "*.spec") { Remove-Item -Force "*.spec" }

# 2. SETUP VENV
Write-Host "2. Creating Fresh Virtual Environment..." -ForegroundColor Green
python -m venv venv_nuclear
# Activate for the current session (simulate activation by using full paths)
$pip = ".\venv_nuclear\Scripts\pip.exe"
$python = ".\venv_nuclear\Scripts\python.exe"
$pyinstaller = ".\venv_nuclear\Scripts\pyinstaller.exe"

# 3. INSTALL
Write-Host "3. Installing Dependencies..." -ForegroundColor Green
& $pip install --upgrade pip
& $pip install customtkinter pillow python-dotenv pyinstaller python-telegram-bot pyautogui pygetwindow pyperclip packaging

# 4. GENERATE ROBUST SPEC FILE
Write-Host "4. Generating Spec File..." -ForegroundColor Green
$spec_content = @"
# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = ['customtkinter', 'PIL', 'PIL.Image', 'PIL.ImageTk', 'ghostsync_core', 'telegram']
tmp_ret = collect_all('customtkinter')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

block_cipher = None

a = Analysis(
    ['ghostsync_gui.py'],
    pathex=[],
    binaries=binaries,
    datas=datas + [('cloudflared.exe', '.')],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='GhostSync_Fixed',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
"@
Set-Content -Path "GhostSync_Nuclear.spec" -Value $spec_content

# 5. BUILD
Write-Host "5. Building..." -ForegroundColor Green
& $pyinstaller --clean --distpath dist_nuclear --workpath build_nuclear GhostSync_Nuclear.spec

Write-Host "6. DONE." -ForegroundColor Cyan
Write-Host "Executable is at: dist_nuclear\GhostSync_Fixed.exe"
