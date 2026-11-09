"""Gemeinsame Hell-/Dunkel-Darstellung für beide Signum-Werkzeuge (ohne Zusatzpakete)."""
from __future__ import annotations

import json
import os
from pathlib import Path
import tkinter as tk
from tkinter import ttk

MODES = ("System", "Hell", "Dunkel")


def settings_path() -> Path:
    base = Path(os.environ.get("APPDATA") or Path.home())
    return base / "Signum-Textfinder" / "settings.json"


def load_mode() -> str:
    try:
        mode = json.loads(settings_path().read_text(encoding="utf-8")).get("theme", "System")
        return mode if mode in MODES else "System"
    except (OSError, ValueError, TypeError, AttributeError):
        return "System"


def save_mode(mode: str) -> None:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    try:
        existing = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(existing, dict):
            data = existing
    except (OSError, ValueError, TypeError):
        pass
    data["theme"] = mode
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def windows_dark_mode() -> bool:
    if os.name != "nt":
        return False
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        with key:
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return int(value) == 0
    except (OSError, ValueError):
        return False


class ThemeController:
    def __init__(self, root: tk.Tk, tree: ttk.Treeview | None = None):
        self.root = root
        self.tree = tree
        self.mode = tk.StringVar(root, value=load_mode())
        self.style = ttk.Style(root)
        self.dark = None
        self.apply()
        self.root.after(2000, self._check_system)

    def chooser(self, parent: ttk.Frame) -> ttk.Frame:
        holder = ttk.Frame(parent)
        ttk.Label(holder, text="Design:").pack(side="left", padx=(0, 6))
        picker = ttk.Combobox(holder, textvariable=self.mode, values=MODES,
                              state="readonly", width=8)
        picker.pack(side="left")
        picker.bind("<<ComboboxSelected>>", self._on_change)
        return holder

    def _on_change(self, _event=None):
        try:
            save_mode(self.mode.get())
        except OSError as exc:
            from tkinter import messagebox
            messagebox.showwarning("Design nicht gespeichert", str(exc), parent=self.root)
        self.apply()

    def _check_system(self):
        if self.root.winfo_exists():
            if self.mode.get() == "System":
                self.apply()
            self.root.after(2000, self._check_system)

    def apply(self):
        dark = self.mode.get() == "Dunkel" or (
            self.mode.get() == "System" and windows_dark_mode())
        if dark == self.dark:
            return
        self.dark = dark
        bg = "#24272d" if dark else "#f3f3f3"
        fg = "#f1f1f1" if dark else "#202020"
        field = "#30343b" if dark else "#ffffff"
        muted = "#aeb7c3" if dark else "#555555"
        select = "#375a83" if dark else "#c9dffc"
        button = "#383d45" if dark else "#e6e6e6"
        self.style.theme_use("clam")
        self.root.configure(background=bg)
        self.style.configure(".", background=bg, foreground=fg)
        self.style.configure("TFrame", background=bg)
        self.style.configure("TLabel", background=bg, foreground=fg)
        self.style.configure("Note.TLabel", background=bg, foreground=muted)
        self.style.configure("TButton", background=button, foreground=fg,
                             bordercolor=muted, lightcolor=button, darkcolor=button)
        self.style.map("TButton",
                       background=[("pressed", select), ("active", select)],
                       foreground=[("disabled", muted)])
        self.style.configure("TCheckbutton", background=bg, foreground=fg)
        self.style.map("TCheckbutton", background=[("active", bg)])
        self.style.configure("TEntry", fieldbackground=field, foreground=fg,
                             insertcolor=fg, bordercolor=muted)
        self.style.configure("TCombobox", fieldbackground=field, foreground=fg,
                             background=button, arrowcolor=fg, bordercolor=muted)
        self.style.map("TCombobox",
                       fieldbackground=[("readonly", field)],
                       foreground=[("readonly", fg)],
                       selectbackground=[("readonly", field)],
                       selectforeground=[("readonly", fg)])
        self.style.configure("Treeview", background=field, fieldbackground=field,
                             foreground=fg, bordercolor=muted)
        self.style.map("Treeview",
                       background=[("selected", select)],
                       foreground=[("selected", fg)])
        self.style.configure("Treeview.Heading", background=button, foreground=fg)
        self.style.map("Treeview.Heading", background=[("active", select)])
        self.style.configure("TProgressbar", background="#478cc9" if dark else "#3478ba",
                             troughcolor=field)
        self.style.configure("TScrollbar", background=button, troughcolor=bg,
                             arrowcolor=fg)
        if self.tree is not None:
            self.tree.tag_configure("ignored", foreground=muted)
        # Die native Dropdown-Liste der ttk-Combobox ist unter Windows
        # teilweise systemgesteuert und folgt nicht in jedem Theme vollständig.
