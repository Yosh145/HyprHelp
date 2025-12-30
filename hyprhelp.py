#!/usr/bin/env python3
import tkinter as tk
import sys
import traceback
import fcntl
import os
import subprocess
import json
import re

#! --- CONFIGURATION ---
APP_TITLE = "hyprhelp"
VERSION = "1.1.0"
# path to your hyprland config file
CONFIG_PATH = os.path.expanduser("~/.config/hypr/hyprland.conf")

# lock file prevents multiple instances running at once
LOCK_FILE = f"/tmp/{APP_TITLE}.lock"
# log file for capturing crash errors
LOG_FILE = f"/tmp/{APP_TITLE}.log"

# color palette for the ui
COLORS = {
    "bg": "#1e1e2e",      
    "fg": "#cdd6f4",        
    "accent": "#89b4fa",    
    "urgent": "#f38ba8",    
    "overlay": "#313244", 
    "warning": "#fab387",
    "mod_text": "#a6e3a1",
    "key_border": "#45475a",
}

#! --- DEFAULT FALLBACK MAP ---
# fallback keybinds used if config parsing fails or finds nothing
DEFAULT_KEY_MAP = {
    "Q": ("Close", "Kill active window"),
    "W": ("Toggle Float", "Toggle floating mode"),
    "E": ("File Manager", "Open File Manaager"),
    "R": ("Menu", "Open Application Launcher"),
    "T": ("Terminal", "Open Terminal"),
    "F": ("Fullscreen", "Toggle fullscreen mode"),
    "M": ("Exit", "Exit Hyprland"),
    "1": ("Workspace 1", "Switch to workspace 1"),
    "2": ("Workspace 2", "Switch to workspace 2"),
    "3": ("Workspace 3", "Switch to workspace 3"),
    "4": ("Workspace 4", "Switch to workspace 4"),
    "5": ("Workspace 5", "Switch to workspace 5"),
    "↑": ("Focus Up", "Move focus up"),
    "↓": ("Focus Down", "Move focus down"),
    "←": ("Focus Left", "Move focus left"),
    "→": ("Focus Right", "Move focus right"),
}

class ConfigParser:
    """
    Parses hyprland.conf for binds with specific comment syntax:
    bind = MOD, KEY, exec, cmd # [Title] Description
    """
    def __init__(self, path):
        self.path = path
        self.key_map = {}
        self.mod_key = "SUPER" # default modifier key

    def parse(self):
        # check if config file exists
        if not os.path.exists(self.path):
            return self.mod_key, {}

        # regex to find the variable defining the mod key (e.g. $mainMod = SUPER)
        re_mod_var = re.compile(r'^\s*\$(\w+)\s*=\s*(\w+)')
        
        # regex to capture the bind line parts: mods, key, command, and comment
        re_bind = re.compile(r'^\s*bind\s*=\s*([^,]*),\s*([^,]*),\s*(.*?)(\s*#\s*(.*))?$')
        
        # regex to extract title and description from the comment brackets
        re_comment = re.compile(r'\[(.*?)\]\s*(.*)')

        try:
            with open(self.path, 'r') as f:
                lines = f.readlines()

            for line in lines:
                line = line.strip()
                if not line: continue

                # check if this line defines the mod key variable
                mod_match = re_mod_var.match(line)
                if mod_match:
                    var_name = mod_match.group(1)
                    val = mod_match.group(2)
                    if var_name == "mainMod":
                        self.mod_key = val
                    continue

                # check if this line is a keybind definition
                bind_match = re_bind.match(line)
                if bind_match:
                    mods = bind_match.group(1).strip()
                    key_raw = bind_match.group(2).strip()
                    comment_raw = bind_match.group(5)

                    # skip binds that don't use the main modifier key
                    if "$mainMod" not in mods and "SUPER" not in mods:
                        continue

                    # ignore mouse buttons to avoid clutter
                    if "mouse" in key_raw: continue

                    # normalize key names to be uppercase and use arrows
                    key = key_raw.upper()
                    if key == "LEFT": key = "←"
                    elif key == "RIGHT": key = "→"
                    elif key == "UP": key = "↑"
                    elif key == "DOWN": key = "↓"
                    elif key == "RETURN": key = "ENTER"

                    # temporary placeholders for title and description
                    title = ""
                    desc = ""
                    
                    # if a comment exists, try to parse the [Title] Description format
                    if comment_raw:
                        c_match = re_comment.match(comment_raw)
                        if c_match:
                            title = c_match.group(1).strip()
                            desc = c_match.group(2).strip()
                        else:
                            # comment exists but doesn't match format, ignore it
                            pass 
                    
                    # only add to map if we successfully found a title
                    if title:
                        self.key_map[key] = (title, desc)
                        
        except Exception:
            # log parsing errors but don't crash the app
            traceback.print_exc()
            
        return self.mod_key, self.key_map

# writes crash info to a log file for debugging
def log_error(exc):
    try:
        with open(LOG_FILE, "w") as f:
            f.write(traceback.format_exc())
    except IOError:
        pass

class HyprHelp:
    def __init__(self):
        # prevent multiple instances from opening
        self._acquire_lock()

        # parse the config file to get keybinds
        parser = ConfigParser(CONFIG_PATH)
        self.detected_mod, parsed_map = parser.parse()
        
        # use the parsed map if valid, otherwise fallback to defaults
        if parsed_map:
            self.key_map = parsed_map
        else:
            self.key_map = DEFAULT_KEY_MAP
            self.detected_mod = "SUPER (Default)"

        # initialize the main window
        self.app = tk.Tk()
        self.app.title(APP_TITLE)
        self.app.geometry("600x500") 
        self.app.configure(bg=COLORS["bg"])

        # group window with app title for wayland compositors
        try:
            self.app.tk.call('wm', 'group', '.', APP_TITLE)
        except tk.TclError:
            pass

        # initialize state variables
        self.monitor_name = self._get_active_monitor()
        self.locked_key = None
        self.key_widgets = {}
        
        # build the visual interface
        self._build_ui()

        # bind global click to clear locks and escape to close app
        self.app.bind("<Button-1>", lambda e: self.clear_lock())
        self.app.bind("<Escape>", lambda e: self.app.destroy())

    def _acquire_lock(self):
        # tries to lock a temp file, exits if already locked
        try:
            self.lock_fp = open(LOCK_FILE, 'w')
            fcntl.lockf(self.lock_fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError:
            sys.exit(0)

    def _get_active_monitor(self):
        # asks hyprctl for the currently focused monitor name
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
        # header frame containing title and mod key info
        header_frame = tk.Frame(self.app, bg=COLORS["bg"])
        header_frame.pack(pady=(25, 5))

        tk.Label(
            header_frame, 
            text=APP_TITLE, 
            fg=COLORS["accent"], 
            bg=COLORS["bg"], 
            font=("Inter", 24, "bold")
        ).pack()

        tk.Label(
            header_frame,
            text=f"Current Modifier: {self.detected_mod}",
            fg=COLORS["mod_text"],
            bg=COLORS["bg"],
            font=("Inter", 10, "bold")
        ).pack(pady=(2, 0))

        # fixed-height info frame to prevent ui jumping when text changes
        info_frame = tk.Frame(self.app, bg=COLORS["bg"], height=80)
        info_frame.pack(pady=(10, 0), fill="x")
        info_frame.pack_propagate(False)

        self.info_title = tk.Label(
            info_frame, 
            text="", 
            fg=COLORS["warning"], 
            bg=COLORS["bg"], 
            font=("Inter", 16, "bold")
        )
        self.info_title.pack(pady=(5, 0))
        
        self.info_desc = tk.Label(
            info_frame, 
            text="Hover a key to preview | Click to lock", 
            fg=COLORS["fg"], 
            bg=COLORS["bg"], 
            font=("Inter", 12), 
            wraplength=700
        )
        self.info_desc.pack(pady=5)

        # main container for the keyboard grid
        self.grid_container = tk.Frame(self.app, bg=COLORS["bg"])
        self.grid_container.pack(expand=True, pady=20)
        
        self._create_keys()

        # footer frame with monitor info and version
        footer = tk.Frame(self.app, bg=COLORS["bg"])
        footer.pack(side="bottom", fill="x", padx=30, pady=20)
        
        tk.Label(
            footer, 
            text=f"Display: {self.monitor_name}", 
            fg=COLORS["accent"], 
            bg=COLORS["bg"], 
            font=("Inter", 10)
        ).pack(side="left")

        tk.Label(
            footer, 
            text=f"v{VERSION}", 
            fg="#585b70", 
            bg=COLORS["bg"], 
            font=("Inter", 10)
        ).pack(side="right")

    def _create_keys(self):
        # create function keys row
        f_row_frame = tk.Frame(self.grid_container, bg=COLORS["bg"])
        f_row_frame.grid(row=0, column=0, columnspan=12, pady=(0, 15))
        
        f_keys = ["F1","F2","F3","F4","F5","F6","F7","F8","F9","F10","F11","F12"]
        for k in f_keys:
            self._render_key(f_row_frame, k, width=5, pack=True)

        # create number row
        nums = ["1","2","3","4","5","6","7","8","9","0"]
        for i, k in enumerate(nums):
            self._render_key(self.grid_container, k, row=1, col=i)

        # create qwerty row
        qwerty = ["Q","W","E","R","T","Y","U","I","O","P"]
        for i, k in enumerate(qwerty):
            self._render_key(self.grid_container, k, row=2, col=i)

        # create asdf row plus up arrow
        asdf = ["A","S","D","F","G","H","J","K","L"]
        for i, k in enumerate(asdf):
            self._render_key(self.grid_container, k, row=3, col=i)
        
        self._render_key(self.grid_container, "↑", row=3, col=10)

        # create zxcv row plus rest of arrow cluster
        zxcv = ["Z","X","C","V","B","N","M"]
        for i, k in enumerate(zxcv):
            self._render_key(self.grid_container, k, row=4, col=i)
            
        self._render_key(self.grid_container, "←", row=4, col=9) 
        self._render_key(self.grid_container, "↓", row=4, col=10) 
        self._render_key(self.grid_container, "→", row=4, col=11)

        # set minimum width for columns to keep grid uniform
        for i in range(12):
            self.grid_container.grid_columnconfigure(i, minsize=60)

    def _render_key(self, parent, key, row=None, col=None, pack=False, width=5):
        w = width
        
        # check if key has a binding to determine styling
        has_binding = key in self.key_map
        bg_color = COLORS["overlay"] if has_binding else COLORS["bg"]
        fg_color = COLORS["fg"] if has_binding else "#45475a" # dim text if unbound
        relief = "ridge" if has_binding else "flat"
        
        btn = tk.Label(
            parent, 
            text=key, 
            width=w, 
            height=2, 
            relief=relief,
            bd=1 if has_binding else 0,
            highlightthickness=0,
            bg=bg_color,
            fg=fg_color,
            font=("Inter", 13, "bold")
        )
        
        if pack:
            btn.pack(side="left", padx=2, pady=2)
        else:
            btn.grid(row=row, column=col, padx=2, pady=2, sticky="nsew")

        # only attach event listeners if the key is actually bound
        if has_binding:
            self.key_widgets[key] = btn
            btn.bind("<Enter>", lambda e, k=key: self.show_info(k))
            btn.bind("<Leave>", lambda e, k=key: self.hide_info(k))
            btn.bind("<Button-1>", lambda e, k=key: self.toggle_lock(k, e))

    def show_info(self, key):
        # ignore hover if another key is locked
        if self.locked_key and self.locked_key != key: 
            return
        
        if key in self.key_map:
            title, desc = self.key_map[key]
            self.info_title.config(text=f"{self.detected_mod} + {key}: {title}")
            self.info_desc.config(text=desc)
            
            # highlight key orange on hover
            if not self.locked_key:
                self.key_widgets[key].config(bg=COLORS["warning"], fg=COLORS["bg"])

    def hide_info(self, key):
        # reset text only if no key is locked
        if not self.locked_key:
            self.info_title.config(text="")
            self.info_desc.config(text="Hover a key to preview | Click to lock")
            self.key_widgets[key].config(bg=COLORS["overlay"], fg=COLORS["fg"])

    def toggle_lock(self, key, event):
        # unlock if clicking the already locked key
        if self.locked_key == key:
            self.clear_lock()
            return "break"
        
        # reset previously locked key visual
        if self.locked_key: 
            self.key_widgets[self.locked_key].config(bg=COLORS["overlay"], fg=COLORS["fg"])
            
        # set new lock
        self.locked_key = key
        self.key_widgets[key].config(bg=COLORS["accent"], fg=COLORS["bg"])
        
        if key in self.key_map:
            title, desc = self.key_map[key]
            self.info_title.config(text=f"LOCKED: {title}")
            self.info_desc.config(text=desc)
        
        return "break"

    def clear_lock(self):
        # resets the ui to default state
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