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
    """Tk-Icon setzen und unter Windows beide nativen Fenster-Icons aktualisieren."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    icon_path = base / "images" / "logo.ico"
    if not icon_path.is_file():
        return
    try:
        window.iconbitmap(default=str(icon_path))
    except tk.TclError:
        pass

    if sys.platform == "win32":
        # Tk verwendet ein eigenes Windows-Toplevel (Wrapper) um das Tk-Widget.
        # Die Taskleiste kann dessen Icon statt des Tk-Widget-Icons verwenden.
        window.after_idle(lambda: _set_native_window_icons(window, icon_path))


def _set_native_window_icons(window: tk.Tk, icon_path: Path) -> None:
    """WM_SETICON an Tk-Fenster und Windows-Wrapper senden (32-/64-Bit-sicher)."""
    if not window.winfo_exists():
        return
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.GetParent.argtypes = [wintypes.HWND]
        user32.GetParent.restype = wintypes.HWND
        user32.GetSystemMetrics.argtypes = [ctypes.c_int]
        user32.GetSystemMetrics.restype = ctypes.c_int
        user32.LoadImageW.argtypes = [
            wintypes.HINSTANCE, wintypes.LPCWSTR, wintypes.UINT,
            ctypes.c_int, ctypes.c_int, wintypes.UINT,
        ]
        user32.LoadImageW.restype = wintypes.HANDLE
        user32.SendMessageW.argtypes = [
            wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM,
        ]
        user32.SendMessageW.restype = wintypes.LPARAM

        IMAGE_ICON = 1
        LR_LOADFROMFILE = 0x0010
        WM_SETICON = 0x0080
        ICON_SMALL, ICON_BIG = 0, 1
        SM_CXICON, SM_CYICON = 11, 12
        SM_CXSMICON, SM_CYSMICON = 49, 50

        hwnd = window.winfo_id()
        wrapper_hwnd = user32.GetParent(hwnd)
        targets = {hwnd}
        if wrapper_hwnd:
            targets.add(wrapper_hwnd)

        # Handle am Fenster halten: WM_SETICON übernimmt nicht deren Besitz.
        handles = []
        for icon_kind, width_metric, height_metric in (
            (ICON_SMALL, SM_CXSMICON, SM_CYSMICON),
            (ICON_BIG, SM_CXICON, SM_CYICON),
        ):
            handle = user32.LoadImageW(
                None, str(icon_path), IMAGE_ICON,
                user32.GetSystemMetrics(width_metric),
                user32.GetSystemMetrics(height_metric),
                LR_LOADFROMFILE,
            )
            if handle:
                handles.append(handle)
                for target in targets:
                    user32.SendMessageW(target, WM_SETICON, icon_kind, handle)
        window._tb2_native_icon_handles = handles
    except (OSError, AttributeError, tk.TclError, ValueError):
        # Auf nicht unterstützten Systemen bleibt das Tk-Icon erhalten.
        pass
