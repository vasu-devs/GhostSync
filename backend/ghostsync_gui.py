import os
import sys
import threading
import logging
import time
import customtkinter as ctk
from pathlib import Path
from PIL import Image
import tkinter.messagebox as messagebox

# ==============================================================================
# DESIGN SYSTEM
# ==============================================================================
THEME_COLOR = "#3B8ED0"  # Modern Blue
FONT_MAIN = "Segoe UI"
FONT_MONO = "Consolas"

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Import backend (New)
import ghostsync_core as ghostsync

class TextHandler(logging.Handler):
    def __init__(self, text_widget):
        logging.Handler.__init__(self)
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        def append():
            self.text_widget.configure(state='normal')
            self.text_widget.insert("end", msg + '\n')
            self.text_widget.configure(state='disabled')
            self.text_widget.see("end")
        try:
            self.text_widget.after(0, append)
        except:
            pass

class GhostSyncApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("GhostSync Pro")
        self.geometry("1000x700")
        self.minsize(800, 600)
        
        # Paths
        self.config_dir = Path(os.path.expanduser("~")) / ".ghostsync"
        self.config_dir.mkdir(exist_ok=True)
        self.config_file = self.config_dir / ".env"
        self.startup_folder = Path(os.getenv('APPDATA')) / "Microsoft/Windows/Start Menu/Programs/Startup"
        self.startup_script = self.startup_folder / "GhostSync_AutoStart.vbs"
        
        self.bot_process = None
        
        # Grid Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.auto_connect_state = False

        # Build UI
        self.setup_sidebar()
        self.setup_home()
        self.setup_logs()
        self.setup_settings()
        
        # Start at Home
        self.select_frame("home")
        
        # Logic
        self.load_config()
        self.log_setup()
        
        # Close Splash Screen if it exists
        try:
            import pyi_splash
            pyi_splash.close()
        except:
            pass

    def setup_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(5, weight=1)

        # Logo / Branding
        self.brand_label = ctk.CTkLabel(
            self.sidebar, 
            text="GhostSync", 
            font=ctk.CTkFont(family=FONT_MAIN, size=24, weight="bold")
        )
        self.brand_label.grid(row=0, column=0, padx=20, pady=(30, 10))
        
        self.brand_sub = ctk.CTkLabel(
            self.sidebar, 
            text="ANTIGRAVITY BRIDGE", 
            font=ctk.CTkFont(family=FONT_MAIN, size=10, weight="bold"),
            text_color="gray60"
        )
        self.brand_sub.grid(row=1, column=0, padx=20, pady=(0, 30))

        # Nav Buttons
        self.btn_home = self.create_nav_btn("Home", "home", 2)
        self.btn_logs = self.create_nav_btn("Terminal", "logs", 3)
        self.btn_settings = self.create_nav_btn("Settings", "settings", 4)
        
        # Theme Toggle
        self.mode_switch = ctk.CTkSwitch(
            self.sidebar, 
            text="Dark Mode", 
            command=self.toggle_mode,
            font=ctk.CTkFont(family=FONT_MAIN, size=12)
        )
        self.mode_switch.grid(row=6, column=0, padx=20, pady=20, sticky="s")
        self.mode_switch.select() # Default Dark

    def create_nav_btn(self, text, view_name, row):
        btn = ctk.CTkButton(
            self.sidebar, 
            text=text, 
            command=lambda: self.select_frame(view_name),
            font=ctk.CTkFont(family=FONT_MAIN, size=14, weight="bold"),
            fg_color="transparent", 
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30"),
            anchor="w",
            height=40
        )
        btn.grid(row=row, column=0, padx=10, pady=5, sticky="ew")
        return btn

    def setup_home(self):
        self.frame_home = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.frame_home.grid_columnconfigure(0, weight=1)

        # -- Hero Section --
        self.hero_card = ctk.CTkFrame(self.frame_home, corner_radius=15, fg_color=("gray85", "gray15"))
        self.hero_card.grid(row=0, column=0, sticky="ew", padx=40, pady=40)
        
        self.lbl_status_title = ctk.CTkLabel(
            self.hero_card, 
            text="System Status", 
            font=ctk.CTkFont(family=FONT_MAIN, size=14, weight="bold"),
            text_color="gray60"
        )
        self.lbl_status_title.pack(anchor="w", padx=25, pady=(25, 5))
        
        self.lbl_status = ctk.CTkLabel(
            self.hero_card, 
            text="OFFLINE", 
            font=ctk.CTkFont(family=FONT_MAIN, size=36, weight="bold"),
            text_color="#ef4444"
        )
        self.lbl_status.pack(anchor="w", padx=25, pady=(0, 25))
        
        self.btn_toggle = ctk.CTkButton(
            self.hero_card, 
            text="CONNECT SERVER", 
            command=self.toggle_service,
            font=ctk.CTkFont(family=FONT_MAIN, size=14, weight="bold"),
            height=45,
            width=160,
            fg_color="#3B8ED0",
            hover_color="#36719f",
            corner_radius=8
        )
        self.btn_toggle.place(relx=1, rely=0.5, anchor="e", x=-25)

        # -- Recent Activity --
        ctk.CTkLabel(
            self.frame_home, 
            text="Recent Activity", 
            font=ctk.CTkFont(family=FONT_MAIN, size=18, weight="bold")
        ).grid(row=1, column=0, sticky="w", padx=40, pady=(10, 10))
        
        self.preview_log = ctk.CTkTextbox(
            self.frame_home, 
            height=300, 
            corner_radius=10,
            font=(FONT_MONO, 12),
            fg_color=("white", "gray10"),
            text_color=("gray20", "gray85"),
            border_width=1,
            border_color=("gray70", "gray25")
        )
        self.preview_log.grid(row=2, column=0, sticky="nsew", padx=40, pady=(0, 40))
        self.preview_log.configure(state="disabled")
        
        self.frame_home.grid_rowconfigure(2, weight=1)

    def setup_logs(self):
        self.frame_logs = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.frame_logs.grid_columnconfigure(0, weight=1)
        self.frame_logs.grid_rowconfigure(1, weight=1)
        
        header = ctk.CTkFrame(self.frame_logs, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=40, pady=30)
        
        ctk.CTkLabel(
            header, text="Terminal Output", 
            font=ctk.CTkFont(family=FONT_MAIN, size=24, weight="bold")
        ).pack(side="left")
        
        ctk.CTkButton(
            header, text="Clear Log", width=100, height=30,
            command=lambda: self.clear_log(),
            fg_color="transparent", border_width=1, text_color=("gray20", "gray80")
        ).pack(side="right")

        self.full_log = ctk.CTkTextbox(
            self.frame_logs,
            font=(FONT_MONO, 13),
            activate_scrollbars=True,
            fg_color=("gray95", "#0d1117"), # Github Dark Dimmed style
            text_color=("gray10", "#c9d1d9")
        )
        self.full_log.grid(row=1, column=0, sticky="nsew", padx=40, pady=(0, 40))
        self.full_log.configure(state="disabled")

    def setup_settings(self):
        self.frame_settings = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        
        ctk.CTkLabel(
            self.frame_settings, 
            text="Configuration", 
            font=ctk.CTkFont(family=FONT_MAIN, size=24, weight="bold")
        ).pack(pady=40, padx=40, anchor="w")
        
        container = ctk.CTkFrame(self.frame_settings, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=40)
        
        # --- Token Input ---
        self.entry_token_var = ctk.StringVar()
        self.create_input_group(container, "Telegram Bot Token", self.entry_token_var, "Paste Token from @BotFather...")
        
        # --- UserID Input ---
        self.entry_uid_var = ctk.StringVar()
        self.create_input_group(container, "Allowed User ID", self.entry_uid_var, "Your Telegram ID (from @userinfobot)...")
        
        # --- Auto Start Switch ---
        self.switch_startup = ctk.CTkSwitch(
            container, 
            text="Run on Windows Startup (24/7 Mode)", 
            command=self.toggle_autostart,
            font=ctk.CTkFont(family=FONT_MAIN, size=14)
        )
        self.switch_startup.pack(anchor="w", pady=20)
        
        # --- Action Buttons ---
        btn_box = ctk.CTkFrame(container, fg_color="transparent")
        btn_box.pack(fill="x", pady=30)
        
        ctk.CTkButton(
            btn_box, 
            text="Save Configuration", 
            command=self.save_config,
            font=ctk.CTkFont(family=FONT_MAIN, size=14, weight="bold"),
            height=45, 
            width=200,
            fg_color="#10b981", hover_color="#059669"
        ).pack(side="left")
        
        # Help Box
        help_box = ctk.CTkFrame(container, fg_color=("gray90", "gray20"), corner_radius=10)
        help_box.pack(fill="x", pady=20)
        
        help_txt = (
            "QUICK SETUP GUIDE:\n\n"
            "1. Telegram ➟ @BotFather ➟ /newbot (Get Token)\n"
            "2. Telegram ➟ @userinfobot (Get User ID)\n"
            "3. Paste above & Save. Click 'Home' to Connect."
        )
        ctk.CTkLabel(
            help_box, text=help_txt, justify="left", 
            font=(FONT_MONO, 12), text_color="gray60"
        ).pack(padx=20, pady=20, anchor="w")

    def create_input_group(self, parent, title, var, placeholder):
        ctk.CTkLabel(
            parent, text=title, 
            font=ctk.CTkFont(family=FONT_MAIN, size=14, weight="bold")
        ).pack(anchor="w", pady=(10, 5))
        
        entry = ctk.CTkEntry(
            parent, textvariable=var, width=500, height=40, placeholder_text=placeholder,
            font=(FONT_MONO, 13), border_width=1
        )
        entry.pack(anchor="w", pady=(0, 20))
        return entry

    # --- LOGIC ---

    def select_frame(self, name):
        # Update Nav Styles
        for btn, n in [(self.btn_home, "home"), (self.btn_logs, "logs"), (self.btn_settings, "settings")]:
            color = ("gray80", "gray25") if name == n else "transparent"
            btn.configure(fg_color=color)

        self.frame_home.grid_forget()
        self.frame_logs.grid_forget()
        self.frame_settings.grid_forget()

        if name == "home": self.frame_home.grid(row=0, column=1, sticky="nsew")
        if name == "logs": self.frame_logs.grid(row=0, column=1, sticky="nsew")
        if name == "settings": self.frame_settings.grid(row=0, column=1, sticky="nsew")

    def toggle_mode(self):
        mode = "Dark" if self.mode_switch.get() == 1 else "Light"
        ctk.set_appearance_mode(mode)
        self.mode_switch.configure(text=f"{mode} Mode")

    def toggle_service(self):
        if self.btn_toggle.cget("text") == "CONNECT SERVER":
            self.start_bot()
        else:
            self.stop_bot()

    def start_bot(self):
        if not self.entry_token_var.get():
            messagebox.showwarning("Setup Required", "Please configure your Bot Token in Settings.")
            self.select_frame("settings")
            return


        self.btn_toggle.configure(text="DISCONNECT", fg_color="#ef4444", hover_color="#b91c1c")
        self.lbl_status.configure(text="ONLINE", text_color="#10b981")
        
        self.auto_connect_state = True
        self._save_state_only()
        
        self.bot_thread = threading.Thread(target=self._run_bot, daemon=True)
        self.bot_thread.start()

    def _run_bot(self):
        logging.info("Initializing Secure Bridge...")
        ghostsync.load_config()
        try:
            ghostsync.main()
        except Exception as e:
            logging.error(f"Critical Error: {e}")
            self.stop_bot()

    def stop_bot(self):
        self.btn_toggle.configure(text="CONNECT SERVER", fg_color="#3B8ED0", hover_color="#36719f")
        self.lbl_status.configure(text="OFFLINE", text_color="#ef4444")
        self.auto_connect_state = False
        self._save_state_only()
        logging.info("Bridge Disconnected.")
        # Actual stop logic requires process restart for this simple architecture

    def clear_log(self):
        self.full_log.configure(state='normal')
        self.full_log.delete("1.0", "end")
        self.full_log.configure(state='disabled')

    def log_setup(self):
        logger = logging.getLogger("GhostSync")
        logger.setLevel(logging.INFO)
        
        fmt_preview = logging.Formatter('%(asctime)s | %(message)s', datefmt='%H:%M:%S')
        h1 = TextHandler(self.preview_log)
        h1.setFormatter(fmt_preview)
        logger.addHandler(h1)
        
        fmt_full = logging.Formatter('%(asctime)s | %(levelname)-7s | %(message)s')
        h2 = TextHandler(self.full_log)
        h2.setFormatter(fmt_full)
        logger.addHandler(h2)

    def load_config(self):
        f = Path("ghostsync.env") if Path("ghostsync.env").exists() else self.config_file
        if f.exists():
            for line in f.read_text().splitlines():
                if "TELEGRAM_BOT_TOKEN=" in line: self.entry_token_var.set(line.split("=",1)[1])
                if "ALLOWED_USER_ID=" in line: self.entry_uid_var.set(line.split("=",1)[1])
                if "AUTO_CONNECT=True" in line: self.auto_connect_state = True
        
        if self.startup_script.exists():
            self.switch_startup.select()
            
        if self.auto_connect_state:
            self.after(500, self.start_bot)

    def _save_state_only(self):
        t, u = self.entry_token_var.get().strip(), self.entry_uid_var.get().strip()
        ac = self.auto_connect_state
        self.config_file.write_text(f"TELEGRAM_BOT_TOKEN={t}\nALLOWED_USER_ID={u}\nAUTO_CONNECT={ac}\n")

    def save_config(self):
        self._save_state_only()
        ghostsync.load_config()
        messagebox.showinfo("Saved", "Configuration updated successfully!")

    def toggle_autostart(self):
        if self.switch_startup.get() == 1:
            exe = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath("ghostsync_gui.py")
            cmd = f'"{exe}"' if getattr(sys, 'frozen', False) else f'"{sys.executable}" "{exe}"'
            self.startup_script.write_text(f'Set WshShell = CreateObject("WScript.Shell")\nWshShell.Run {cmd}, 0')
            logging.info("Auto-Start Enabled")
        else:
            if self.startup_script.exists(): self.startup_script.unlink()
            logging.info("Auto-Start Disabled")

if __name__ == "__main__":
    app = GhostSyncApp()
    app.mainloop()
