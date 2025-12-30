# hyprhelp

A lightweight, dependency-free cheatsheet overlay for Hyprland keybinds.

![alt text](image.png)

`hyprhelp` provides a visual reference for your keybindings. It features a "dim-around" effect, interactive locking, and zero-latency startup using standard Python libraries.

## Prerequisites

You likely already have most of these, but ensure the following are installed:

* **Hyprland** (Tested on v0.40+)
* **Python 3**
* **Tkinter** (Standard Python GUI library)

```bash
# Fedora
sudo dnf install python3-tkinter

# Arch Linux
sudo pacman -S tk

# Debian/Ubuntu
sudo apt install python3-tk
```
 
## Installation
    
Clone the repository (or download the script manually):

```bash
git clone https://github.com/Yosh145/HyprHelp.git ~/.config/hypr/scripts/hyprhelp
```

Make the script executable:

```bash
chmod +x ~/.config/hypr/scripts/hyprhelp/hyprhelp.py
```
## Configuration

To make hyprhelp float, center, and look sharp, you need to add specific rules to your hyprland.conf.

### Open your config file:
```bash
~/.config/hypr/hyprland.conf
```
### Add Window Rules

Add the following lines to your Window Rules section. This forces the window to float, center itself, and dims the background behind it.

```conf
windowrulev2 = float, title:^(hyprhelp)$
windowrulev2 = center, title:^(hyprhelp)$
windowrulev2 = size 920 680, title:^(hyprhelp)$
windowrulev2 = dimaround, title:^(hyprhelp)$
windowrulev2 = stayfocused, title:^(hyprhelp)$
```

### Fix XWayland Scaling (IMPORTANT)

Since this app uses Tkinter (which runs via XWayland), it may look blurry on high-DPI displays unless you disable scaling for XWayland apps.

Add this near the top of your config:
```conf
xwayland {
  force_zero_scaling = true
}
```

### Add the Keybinding

Bind the script to a key (i.e., Super + H). 

> [!NOTE] GDK_BACKEND=x11
> Explicitly set GDK_BACKEND=x11 to ensure maximum compatibility

> Replace `$mainMod` with your MOD key 

```conf
bind = $mainMod, H, exec, env GDK_BACKEND=x11 ~/.config/hypr/scripts/hyprhelp/hyprhelp.py
```

## Usage & Customization
Reload Hyprland
```bash
hyprctl reload
```

Press chosen bind (`SUPER + H` default).

Hover over keys to see what they do.

Click a key to "Lock" the description so you can read it without holding the mouse. Click the background to unlock.

## Editing Keybinds

hyprhelp is designed to be simple. To change the keys displayed, open hyprhelp.py and edit the KEY_MAP dictionary at the top of the file:

```Python
KEY_MAP = {
    "Q": ("Workspace 1", "Jump to your first desktop"),
    "W": ("My Custom App", "Launches my special script"),
    # ...
}
```

## Troubleshooting

### The window is blurry / text is huge: 
Ensure you added xwayland { force_zero_scaling = true } to your hyprland.conf.

### The window doesn't appear: 
Run the script manually in your terminal to check for errors:
```bash
env GDK_BACKEND=x11 ~/.config/hypr/scripts/hyprhelp/hyprhelp.py
```

#### If it crashes with ModuleNotFoundError, you are missing the tkinter package (see Prerequisites).

## License

the idgaf one??

prob MIT idk