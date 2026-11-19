"""Windows-Anwendungskennung und Tk-Fenstersymbol für Skript und PyInstaller."""
from __future__ import annotations

import sys
from pathlib import Path
import tkinter as tk


def configure_app_identity(app_id: str) -> None:
    """Eigene Taskleisten-Identität vor dem Erzeugen des Hauptfensters setzen."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except (AttributeError, OSError):
        pass


def apply_window_icon(window: tk.Tk) -> None:
    """Gebündeltes oder lokales logo.ico als Tk-Fenstersymbol verwenden."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    icon_path = base / "logo.ico"
    if not icon_path.is_file():
        return
    try:
        window.iconbitmap(default=str(icon_path))
    except tk.TclError:
        pass
