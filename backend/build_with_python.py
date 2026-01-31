
import PyInstaller.__main__
import customtkinter
import os
import shutil

# 1. Get the path to customtkinter
ctk_path = os.path.dirname(customtkinter.__file__)
print(f"✅ Found CustomTkinter at: {ctk_path}")

# 2. Clean previous builds
if os.path.exists("build"): shutil.rmtree("build")
# if os.path.exists("dist"): shutil.rmtree("dist") # Avoid permission errors if app is running

# 3. Define the arguments
args = [
    'ghostsync_gui.py',
    '--name=GhostSync_TotalTunnel',
    '--onefile',
    '--noconsole',
    '--clean',
    '--distpath=dist_fixed',
    '--splash=splash.png',
    
    # FORCE the path to be included
    f'--paths={os.path.dirname(ctk_path)}',
    
    # Force Copy the data
    f'--add-data={ctk_path};customtkinter',
    
    # Explicit imports
    '--hidden-import=customtkinter',
    '--hidden-import=PIL',
    '--hidden-import=telegram',
    '--hidden-import=pyautogui',
    
    # Cloudflared if exists
    '--add-data=cloudflared.exe;.' if os.path.exists("cloudflared.exe") else None
]

# Configure cloudflared arg handling
args = [a for a in args if a is not None]

print("🚀 Starting Build with Explicit Paths...")

# 4. Run PyInstaller directly
PyInstaller.__main__.run(args)
