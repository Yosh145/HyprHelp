#!/usr/bin/env python3
import tkinter as tk
import sys
import traceback
import fcntl
import os
import subprocess
import json

#! --- CONFIGURATION ---
APP_TITLE = "hyprhelp"
VERSION = "1.0.1"

# Single instance locking & logging
LOCK_FILE = f"/tmp/{APP_TITLE}.lock"
LOG_FILE = f"/tmp/{APP_TITLE}.log"

COLORS = {
    "bg": "#1e1e2e",      
    "fg": "#cdd6f4",       
    "accent": "#89b4fa",   
    "urgent": "#f38ba8",   
    "overlay": "#313244", 
    "warning": "#fab387",
}

#! Key Bindings Configuration:
#? Format: "Key": ("Title", "Description")
KEY_MAP = {
    "Q": ("Workspace 1", "Switch to workspace 1"),
    "W": ("Workspace 2", "Switch to workspace 2"),
    "E": ("Workspace 3", "Switch to workspace 3"),
    "R": ("Reload", "Reload Hyprland configuration"),
    "T": ("Workspace 4", "Switch to workspace 4"),
    "Y": ("Workspace 5", "Switch to workspace 5"),
    "U": ("Focus Last", "Focus the previously active window"),
    "I": ("Split Ratio", "Adjust the split ratio of windows"),
    "O": ("Editor", "Launch code editor (VS Code)"),
    "P": ("Pseudo", "Toggle pseudo-tiling mode"),
    "A": ("Browser", "Launch web browser (Firefox)"),
    "S": ("Files", "Open file manager"),
    "D": ("Discord", "Launch Discord"),
    "F": ("Fullscreen", "Toggle fullscreen mode"),
    "G": ("Spotify", "Launch music player"),
    "H": ("Help", "Show this keybind helper"),
    "J": ("Orientation", "Toggle split orientation"),
    "K": ("Notepad", "Launch text editor"),
    "L": ("Lock Screen", "Lock the session"),
    "Z": ("Terminal", "Launch terminal emulator"),
    "X": ("Kill", "Close the active window"),
    "C": ("Launcher", "Open application launcher (Rofi)"),
    "V": ("Float", "Toggle floating mode"),
    "B": ("Waybar", "Toggle status bar visibility"),
    "N": ("Notifications", "Open notification center"),
    "M": ("Mute", "Toggle system audio mute")
}

# Logger
def log_error(exc):
    """Logs critical crashes to /tmp/hyprhelp.log for debugging."""
    try:
        with open(LOG_FILE, "w") as f:
            f.write(traceback.format_exc())
    except IOError:
        pass


class HyprHelp:
    def __init__(self):
        self._acquire_lock()

        self.app = tk.Tk()
        self.app.title(APP_TITLE)
        self.app.geometry("920x680")
        self.app.configure(bg=COLORS["bg"])

        try:
            self.app.tk.call('wm', 'group', '.', APP_TITLE)
        except tk.TclError:
            pass

        # Data State
        self.monitor_name = self._get_active_monitor()
        self.locked_key = None
        self.key_widgets = {}
        
        self._build_ui()

        # Global Event Bindings
        # Click background = Clear lock
        self.app.bind("<Button-1>", lambda e: self.clear_lock())
        # Escape (ESC key) (ON HOVER) = Close app
        self.app.bind("<Escape>", lambda e: self.app.destroy())

    def _acquire_lock(self):
        """
        Uses fcntl to lock a temporary file.
        If the file is already locked, another instance is running = Exit.
        """
        try:
            self.lock_fp = open(LOCK_FILE, 'w')
            fcntl.lockf(self.lock_fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError:
            sys.exit(0)

    def _get_active_monitor(self):
        """
        Queries `hyprctl` to find the currently focused monitor name.
        Returns "Unknown" if the command fails or path is invalid.
        """
        try:
            cmd = ["/usr/bin/hyprctl", "-j", "monitors"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            monitors = json.loads(result.stdout)
            for m in monitors:
                if m.get("focused"):
                    return m.get("name", "Unknown")
            return "Unknown"
        except (subprocess.SubprocessError, json.JSONDecodeError, FileNotFoundError):
            return "Unknown"

    def _build_ui(self):
        """Constructs the GUI elements."""
        # Header
        tk.Label(
            self.app, 
            text=APP_TITLE, 
            fg=COLORS["accent"], 
            bg=COLORS["bg"], 
            font=("Inter", 24, "bold")
        ).pack(pady=(35, 5))

        # Info
        self.info_title = tk.Label(
            self.app, 
            text="", 
            fg=COLORS["warning"], 
            bg=COLORS["bg"], 
            font=("Inter", 16, "bold")
        )
        self.info_title.pack(pady=(15, 0))
        
        self.info_desc = tk.Label(
            self.app, 
            text="Hover a key to preview | Click to lock", 
            fg=COLORS["fg"], 
            bg=COLORS["bg"], 
            font=("Inter", 12), 
            wraplength=700
        )
        self.info_desc.pack(pady=20)

        # Keyboard Grid
        self.grid_frame = tk.Frame(self.app, bg=COLORS["bg"])
        self.grid_frame.pack(pady=10, expand=True)
        self._create_keys()

        # Footer
        footer = tk.Frame(self.app, bg=COLORS["bg"])
        footer.pack(side="bottom", fill="x", padx=30, pady=20)
        
        # Monitor Info
        tk.Label(
            footer, 
            text=f"Display: {self.monitor_name}", 
            fg=COLORS["accent"], 
            bg=COLORS["bg"], 
            font=("Inter", 10)
        ).pack(side="left")

        # Version Info
        tk.Label(
            footer, 
            text=f"v{VERSION}", 
            fg="#585b70", 
            bg=COLORS["bg"], 
            font=("Inter", 10)
        ).pack(side="right")

    def _create_keys(self):
        """Generates the visual grid of key widgets."""
        rows = [
            ["Q","W","E","R","T","Y","U","I","O","P"],
            ["A","S","D","F","G","H","J","K","L"],
            ["Z","X","C","V","B","N","M"]
        ]
        
        for row in rows:
            row_frame = tk.Frame(self.grid_frame, bg=COLORS["bg"])
            row_frame.pack()
            
            for key in row:
                btn = tk.Label(
                    row_frame, 
                    text=key, 
                    width=5, 
                    height=2, 
                    relief="flat",
                    bg=COLORS["overlay"], 
                    fg=COLORS["fg"], 
                    font=("Inter", 12, "bold")
                )
                btn.pack(side="left", padx=5, pady=5)
                
                # Register widget for later access
                self.key_widgets[key] = btn
                
                # Bind Interactive Events
                btn.bind("<Enter>", lambda e, k=key: self.show_info(k))
                btn.bind("<Leave>", lambda e, k=key: self.hide_info(k))
                btn.bind("<Button-1>", lambda e, k=key: self.toggle_lock(k, e))

    def show_info(self, key):
        """Updates the info text on hover (unless locked)."""
        if self.locked_key and self.locked_key != key: 
            return
        
        if key in KEY_MAP:
            title, desc = KEY_MAP[key]
            self.info_title.config(text=f"SUPER + {key}: {title}")
            self.info_desc.config(text=desc)
            
            # Highlight key if not locked
            if not self.locked_key:
                self.key_widgets[key].config(bg=COLORS["warning"], fg=COLORS["bg"])

    def hide_info(self, key):
        """Resets the info text when mouse leaves (unless locked)."""
        if not self.locked_key:
            self.info_title.config(text="")
            self.info_desc.config(text="Hover a key to preview | Click to lock")
            self.key_widgets[key].config(bg=COLORS["overlay"], fg=COLORS["fg"])

    def toggle_lock(self, key, event):
        """
        Locks the description of a key. 
        Clicking the same key again unlocks it.
        """
        # Unlock if clicking the locked key
        if self.locked_key == key:
            self.clear_lock()
            return "break"
        
        # If another key was locked reset color
        if self.locked_key: 
            self.key_widgets[self.locked_key].config(bg=COLORS["overlay"], fg=COLORS["fg"])
            
        # Lock that jon
        self.locked_key = key
        self.key_widgets[key].config(bg=COLORS["accent"], fg=COLORS["bg"])
        
        # change description to LOCKED
        title, desc = KEY_MAP[key]
        self.info_title.config(text=f"LOCKED: {title}")
        self.info_desc.config(text=desc)
        
        # Should clear any random locks happening
        return "break"

    def clear_lock(self):
        """Resets the lock state and clears text."""
        if self.locked_key:
            self.key_widgets[self.locked_key].config(bg=COLORS["overlay"], fg=COLORS["fg"])
            self.locked_key = None
            self.info_title.config(text="")
            self.info_desc.config(text="Hover a key to preview | Click to lock")


if __name__ == "__main__":
    try:
        app = HyprHelp()
        app.app.mainloop()
    except Exception as e:
        log_error(e)
        sys.exit(1)