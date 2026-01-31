"""
GhostSync v3.4 - SECURE Telegram to Antigravity Bridge (PROD)
"""

import asyncio
import ctypes
import logging
import os
import re
import subprocess
import sys
import time
import secrets
import hashlib
import threading
from pathlib import Path
from enum import Enum
from typing import Optional, Callable
from datetime import datetime, timedelta

# ==============================================================================
# CONFIGURATION
# ==============================================================================
TELEGRAM_BOT_TOKEN = ""
ALLOWED_USER_ID = 0

def load_config():
    """Load configuration from .env file."""
    global TELEGRAM_BOT_TOKEN, ALLOWED_USER_ID
    
    # Try loading from local .env first (dev mode)
    env_path = Path(__file__).parent / ".env"
    
    # If not found, try user home directory (production mode)
    if not env_path.exists():
        env_path = Path(os.path.expanduser("~")) / ".ghostsync" / ".env"
    
    if env_path.exists():
        try:
            content = env_path.read_text(encoding='utf-8')
            for line in content.splitlines():
                if "=" in line and not line.strip().startswith("#"):
                    key, val = line.split("=", 1)
                    key, val = key.strip(), val.strip().strip('"\'')
                    if key == "TELEGRAM_BOT_TOKEN":
                        TELEGRAM_BOT_TOKEN = val
                    elif key == "ALLOWED_USER_ID":
                        try:
                            ALLOWED_USER_ID = int(val)
                        except ValueError:
                            pass
        except Exception as e:
            pass

load_config()

# Security settings
TUNNEL_TIMEOUT_MINUTES = 30
MAX_REQUESTS_PER_MINUTE = 10
SCREENSHOT_AUTO_DELETE = True

# ==============================================================================
# LOGGING
# ==============================================================================
log_path = Path(__file__).parent / "ghostsync.log"

class SanitizingFormatter(logging.Formatter):
    SENSITIVE_PATTERNS = [
        (r'token=[\w-]+', 'token=***'),
        (r'password["\']?\s*[:=]\s*["\']?[\w]+', 'password=***'),
        (r'api[_-]?key["\']?\s*[:=]\s*["\']?[\w]+', 'api_key=***'),
    ]
    def format(self, record):
        msg = super().format(record)
        for pattern, replacement in self.SENSITIVE_PATTERNS:
            msg = re.sub(pattern, replacement, msg, flags=re.IGNORECASE)
        return msg

handler = logging.FileHandler(log_path, encoding='utf-8')
handler.setFormatter(SanitizingFormatter('%(asctime)s | %(levelname)-7s | %(message)s'))

logging.basicConfig(
    format='%(asctime)s | %(levelname)-7s | %(message)s',
    level=logging.INFO,
    handlers=[handler, logging.StreamHandler()]
)
log = logging.getLogger("GhostSync")

# ==============================================================================
# DEPENDENCIES
# ==============================================================================
try:
    import pyautogui
    import pygetwindow as gw
    import pyperclip
    from PIL import ImageChops, Image
    from telegram import Update
    from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
except ImportError as e:
    log.error(f"Critical Import Error: {e}")
    if getattr(sys, 'frozen', False):
        sys.exit(1)

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05

# ==============================================================================
# RATE LIMITER
# ==============================================================================
class RateLimiter:
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self.requests = {}

    def is_allowed(self, user_id: int) -> bool:
        now = time.time()
        if user_id not in self.requests:
            self.requests[user_id] = []
        self.requests[user_id] = [t for t in self.requests[user_id] if now - t < self.window]
        if len(self.requests[user_id]) >= self.max_requests:
            return False
        self.requests[user_id].append(now)
        return True
    
rate_limiter = RateLimiter(MAX_REQUESTS_PER_MINUTE, 60)

# ==============================================================================
# WINDOWS API
# ==============================================================================
user32 = ctypes.windll.user32
SW_RESTORE = 9

class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long)]

def get_foreground_hwnd() -> int:
    return user32.GetForegroundWindow()

def get_window_title(hwnd: int) -> str:
    length = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value

def is_window_valid(hwnd: int) -> bool:
    return bool(user32.IsWindow(hwnd))

def focus_window_by_hwnd(hwnd: int) -> bool:
    if not is_window_valid(hwnd): return False
    try:
        user32.ShowWindow(hwnd, SW_RESTORE)
        time.sleep(0.1)
        user32.SetForegroundWindow(hwnd)
        time.sleep(0.3)
        return True
    except:
        return False

# ==============================================================================
# SECURE CLOUDFLARE TUNNEL
# ==============================================================================
class SecureTunnel:
    CLOUDFLARED_PATH = Path(__file__).parent / "cloudflared.exe"
    
    def __init__(self):
        self.processes = {}
    
    def ensure_cloudflared(self) -> bool:
        if self.CLOUDFLARED_PATH.exists(): return True
        log.info("Downloading cloudflared...")
        try:
            import urllib.request
            url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
            urllib.request.urlretrieve(url, str(self.CLOUDFLARED_PATH))
            return True
        except Exception as e:
            log.error(f"Download failed: {e}")
            return False
    
    def create_tunnel(self, port: int) -> Optional[str]:
        self.kill_all()
        if not self.ensure_cloudflared(): return None
        
        try:
            log.info(f"Creating tunnel for port {port}...")
            proc = subprocess.Popen(
                [str(self.CLOUDFLARED_PATH), "tunnel", "--url", f"http://localhost:{port}"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            start_time = time.time()
            found_url = None
            while time.time() - start_time < 30:
                line = proc.stdout.readline()
                if not line:
                    time.sleep(0.1)
                    continue
                match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
                if match:
                    found_url = match.group(0)
                    break
            
            if found_url:
                self.processes[port] = {"process": proc, "url": found_url, "created": datetime.now()}
                return found_url
            proc.terminate()
            return None
        except Exception as e:
            log.error(f"Tunnel error: {e}")
            return None

    def is_port_open(self, port: int) -> bool:
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                return s.connect_ex(('localhost', port)) == 0
        except:
            return False

    def detect_dev_server(self) -> Optional[int]:
        common_ports = [3000, 3001, 3002, 5173, 5174, 8000, 8080]
        try:
            result = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, shell=True)
            for port in common_ports:
                if f":{port}" in result.stdout and "LISTENING" in result.stdout:
                    return port
        except: pass
        return None

    def kill_all(self):
        for port in list(self.processes.keys()):
            try:
                self.processes[port]["process"].terminate()
                del self.processes[port]
            except: pass

tunnel = SecureTunnel()

# ==============================================================================
# SECURE FILE HANDLING
# ==============================================================================
def secure_delete(filepath: str):
    try:
        path = Path(filepath)
        if path.exists():
            path.unlink()
    except: pass

def take_screenshot_secure() -> str:
    random_suffix = secrets.token_hex(4)
    path = str(Path(__file__).parent / f"ss_{random_suffix}.png")
    try:
        pyautogui.screenshot().save(path)
        return path
    except: return ""

# ==============================================================================
# ANTIGRAVITY CONTROLLER
# ==============================================================================
class AcceptDenyDetector:
    def detect_accept_deny_prompt(self, screenshot: Image.Image) -> Optional[dict]:
        # Simple color-based detection for Green/Red buttons
        width, height = screenshot.size
        pixels = screenshot.load()
        search_left = int(width * 0.5)
        search_top = int(height * 0.2)
        
        green_pos = None
        red_pos = None
        
        for y in range(search_top, height, 20):
            for x in range(search_left, width, 20):
                r, g, b = pixels[x, y][:3]
                if g > 150 and g > r * 1.5 and g > b * 1.5: green_pos = (x, y)
                if r > 150 and r > g * 1.5 and r > b * 1.5: red_pos = (x, y)
                if green_pos and red_pos: break
            if green_pos and red_pos: break
            
        if green_pos and red_pos:
            return {"accept_pos": green_pos, "deny_pos": red_pos}
        return None

    def click_accept(self, pos): pyautogui.click(pos[0], pos[1])
    def click_deny(self, pos): pyautogui.click(pos[0], pos[1])

detector = AcceptDenyDetector()

class AntigravityController:
    ANTIGRAVITY_EXE = str(Path(os.path.expanduser("~")) / "AppData/Local/Programs/Antigravity/Antigravity.exe")

    def __init__(self):
        self.hwnd = None
        self.project_path = None
        self.latest_stream_ss = None

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        log.info(f"Received /start from {update.effective_user.id}")
        user_id = update.effective_user.id
        set_user_state(user_id, UserState.WAITING_FOR_PATH)
        
        # Don't open Antigravity yet - wait for folder path
        await update.message.reply_text("👻 **GhostSync Active**\nSend the **project folder path** to open Antigravity.")

    def open_folder(self, path: str):
        try:
            subprocess.Popen([self.ANTIGRAVITY_EXE, path])
            time.sleep(5)
            hwnds = self._find_antigravity_windows()
            if hwnds:
                self.hwnd = hwnds[0]
                self.project_path = path
                ss_path = take_screenshot_secure()
                return True, "Opened", ss_path
            return False, "Window not found", None
        except Exception as e:
            return False, str(e), None

    def _find_antigravity_windows(self):
        hwnds = []
        def enum_callback(hwnd, _):
            if user32.IsWindowVisible(hwnd) and "Antigravity" in get_window_title(hwnd):
                hwnds.append(hwnd)
            return True
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
        user32.EnumWindows(WNDENUMPROC(enum_callback), 0)
        return hwnds

    def send_prompt(self, text, ask_user_callback):
        log.info(f"--- STARTING GUARANTEED FOCUS SEQUENCE for: {text[:20]}... ---")
        
        if not self.hwnd or not is_window_valid(self.hwnd):
            log.info("HWND invalid, re-detecting Antigravity window...")
            hwnds = self._find_antigravity_windows()
            if hwnds:
                self.hwnd = hwnds[0]
            else:
                return {"ai_reply": "❌ Error: Antigravity window not found.", "local_url": None, "tunnel_url": None, "screenshot": None}

        try:
            # Get window rectangle for coordinate calculations
            rect = RECT()
            user32.GetWindowRect(self.hwnd, ctypes.byref(rect))
            win_left, win_top = rect.left, rect.top
            win_width = rect.right - rect.left
            win_height = rect.bottom - rect.top
            log.info(f"Window rect: {win_left},{win_top} size {win_width}x{win_height}")
            
            # 1. Force Awake & Foreground
            log.info("Step 1: Force window to foreground")
            if user32.IsIconic(self.hwnd):
                user32.ShowWindow(self.hwnd, 9)  # SW_RESTORE
            user32.SetForegroundWindow(self.hwnd)
            time.sleep(0.5)
            
            # 2. Click on the window center first to ensure it's focused
            center_x = win_left + win_width // 2
            center_y = win_top + win_height // 2
            log.info(f"Step 2: Click center to focus window ({center_x}, {center_y})")
            pyautogui.click(center_x, center_y)
            time.sleep(0.3)
            
            # 3. Use keyboard shortcut Ctrl+Shift+I to open Antigravity chat
            # (This is the inline chat shortcut in VS Code based editors)
            log.info("Step 3: Open inline chat with Ctrl+I")
            pyautogui.hotkey('ctrl', 'i')
            time.sleep(1.0)
            
            # 4. If that didn't work, try clicking on the chat panel area
            # Antigravity chat is typically on the right side, bottom portion
            # Chat input is at the bottom of the right panel
            chat_input_x = win_left + int(win_width * 0.75)  # 75% from left (right panel)
            chat_input_y = win_top + int(win_height * 0.85)   # 85% from top (bottom of panel)
            log.info(f"Step 4: Click chat input area ({chat_input_x}, {chat_input_y})")
            pyautogui.click(chat_input_x, chat_input_y)
            time.sleep(0.3)
            
            # 5. Triple-click to select all in current input, then delete
            log.info("Step 5: Clear any existing text (triple-click + delete)")
            pyautogui.click(chat_input_x, chat_input_y, clicks=3)
            time.sleep(0.2)
            pyautogui.press('delete')
            time.sleep(0.2)
            
            # 6. Type the prompt using pyautogui.write() for reliability
            # First copy to clipboard as backup
            log.info(f"Step 6: Type prompt ({len(text)} chars)")
            pyperclip.copy(text)
            
            # Use Ctrl+V to paste (more reliable than typing for special characters)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.5)
            
            # 7. Take a screenshot to verify text was entered
            log.info("Step 7: Verifying text entry...")
            verify_ss = pyautogui.screenshot()
            verify_ss.save(str(Path(__file__).parent / "verify_prompt.png"))
            
            # 8. Submit with Enter
            log.info("Step 8: Submit prompt (Enter)")
            pyautogui.press('enter')
            time.sleep(0.5)
            
            log.info("=== PROMPT SEQUENCE COMPLETE ===")

        except Exception as e:
            log.error(f"CRITICAL: Focus sequence failed: {e}")
            return {"ai_reply": f"❌ Focus Error: {e}", "local_url": None, "tunnel_url": None, "screenshot": None}

        self._wait_with_detection(ask_user_callback)
        
        # Capture AI Text (if possible via clipboard)
        ai_reply = "✅ Task processed."
        try:
            pyautogui.hotkey('ctrl', 'a')
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(0.1)
            ai_reply = pyperclip.paste()
        except: pass

        # TUNNELING LOGIC
        local_url = None
        tunnel_url = None
        
        # 1. Detect port in text
        port_match = re.search(r':(\d{4,5})', ai_reply)
        detected_port = int(port_match.group(1)) if port_match else tunnel.detect_dev_server()
        
        if detected_port:
            local_url = f"http://localhost:{detected_port}"
            # Wait for port to be ready
            for _ in range(10):
                if tunnel.is_port_open(detected_port):
                    tunnel_url = tunnel.create_tunnel(detected_port)
                    break
                time.sleep(1)

        ss_path = take_screenshot_secure()
        return {
            "ai_reply": ai_reply,
            "local_url": local_url,
            "tunnel_url": tunnel_url,
            "screenshot": ss_path
        }

    def _wait_with_detection(self, ask_user_callback, timeout=180):
        start = time.time()
        last_ss = pyautogui.screenshot()
        stable_since = None
        last_check = 0
        
        while time.time() - start < timeout:
            time.sleep(1)
            current_ss = pyautogui.screenshot()
            
            # Streaming SS
            stream_path = str(Path(__file__).parent / "stream_temp.png")
            current_ss.save(stream_path)
            self.latest_stream_ss = stream_path

            # Detect blocking prompts
            if time.time() - last_check > 4:
                last_check = time.time()
                button_info = detector.detect_accept_deny_prompt(current_ss)
                if button_info:
                    response = ask_user_callback(stream_path, button_info)
                    focus_window_by_hwnd(self.hwnd)
                    if response == "deny": detector.click_deny(button_info["deny_pos"])
                    else: detector.click_accept(button_info["accept_pos"])
                    continue

            # Check stability
            diff = ImageChops.difference(last_ss, current_ss)
            if not diff.getbbox():
                if stable_since is None: stable_since = time.time()
                elif time.time() - stable_since >= 3: return
            else:
                stable_since = None
                last_ss = current_ss

controller = AntigravityController()

# ==============================================================================
# USER STATE
# ==============================================================================
class UserState(Enum):
    IDLE = "idle"
    WAITING_FOR_PATH = "waiting_for_path"
    WAITING_FOR_CONFIRMATION = "waiting_for_confirmation"
    READY_FOR_PROMPTS = "ready_for_prompts"

user_states = {}

def get_user_state(user_id):
    if user_id not in user_states: user_states[user_id] = {"state": UserState.IDLE, "path": None}
    return user_states[user_id]

def set_user_state(user_id, state, path=None):
    user_states[user_id] = {"state": state, "path": path or user_states.get(user_id, {}).get("path")}

# ==============================================================================
# TELEGRAM HANDLERS
# ==============================================================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    log.info(f"Msg from {user_id}: {update.message.text[:50]}")
    if ALLOWED_USER_ID != 0 and user_id != ALLOWED_USER_ID: return
    
    text = update.message.text
    state_data = get_user_state(user_id)
    state = state_data["state"]

    if state == UserState.WAITING_FOR_PATH:
        msg = await update.message.reply_text("📂 Opening project...")
        success, info, screenshot = await asyncio.to_thread(controller.open_folder, text)
        if success:
            await update.message.reply_photo(screenshot, caption=f"Opened: {text}\nConfirm? (yes/no)")
            secure_delete(screenshot)
            set_user_state(user_id, UserState.WAITING_FOR_CONFIRMATION, text)
        else:
            await update.message.reply_text(f"❌ Error: {info}")

    elif state == UserState.WAITING_FOR_CONFIRMATION:
        if text.lower() in ['y', 'yes']:
            set_user_state(user_id, UserState.READY_FOR_PROMPTS, state_data["path"])
            await update.message.reply_text("✅ Ready for prompts.")
        else:
            set_user_state(user_id, UserState.WAITING_FOR_PATH)
            await update.message.reply_text("Send path again.")

    elif state == UserState.READY_FOR_PROMPTS:
        if not rate_limiter.is_allowed(user_id):
            await update.message.reply_text("⏱️ Rate limited.")
            return

        status_msg = await update.message.reply_text("🤖 Working...")
        
        def run_task():
            return controller.send_prompt(text, lambda s, b: "accept")

        # Run the blocking task in a thread and await it
        log.info(f"Executing prompt task for: {text[:30]}...")
        result = await asyncio.to_thread(run_task)
        log.info("Prompt task completed!")
        
        await context.bot.delete_message(update.effective_chat.id, status_msg.message_id)

        reply = result["ai_reply"][:1000]
        if result["local_url"]: reply += f"\n\n🏠 **Local:** {result['local_url']}"
        if result["tunnel_url"]: reply += f"\n🌐 **Public:** {result['tunnel_url']}"

        if result["screenshot"]:
            await update.message.reply_photo(result["screenshot"], caption=reply)
            secure_delete(result["screenshot"])
        else:
            await update.message.reply_text(reply)

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await controller.cmd_start(update, context)

def main():
    log.info("--- BOT MAIN STARTED ---")
    if not TELEGRAM_BOT_TOKEN: 
        log.error("CRITICAL: No Telegram Token Found!")
        return

    # Force new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    log.info("Building Application...")
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    log.info("Starting Polling...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
