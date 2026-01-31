# -*- mode: python ; coding: utf-8 -*-
# GhostSync Production Build Spec

import sys
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# Collect all customtkinter data files
ctk_datas, ctk_binaries, ctk_hiddenimports = collect_all('customtkinter')

a = Analysis(
    ['ghostsync_gui.py'],
    pathex=[],
    binaries=ctk_binaries,
    datas=ctk_datas + [
        ('splash.png', '.'),
        ('cloudflared.exe', '.'),
    ],
    hiddenimports=ctk_hiddenimports + [
        'PIL._tkinter_finder',
        'telegram',
        'telegram.ext',
        'httpx',
        'pyautogui',
        'pygetwindow',
        'pyperclip',
        'pyscreeze',
        'pytweening',
        'mouseinfo',
    ],
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

# Single-file executable with splash screen
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='GhostSync',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='splash.png',  # App icon
    version='version_info.txt',
)
