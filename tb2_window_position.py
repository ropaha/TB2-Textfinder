"""Fenster auf dem aktiven Windows-Monitor bzw. über ihrem Elternfenster zentrieren."""
from __future__ import annotations

import sys
import tkinter as tk


def _work_area(window: tk.Misc, parent: tk.Misc | None = None) -> tuple[int, int, int, int]:
    """Arbeitsbereich des relevanten Monitors; Fallback auf Tk-Bildschirm."""
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            class POINT(ctypes.Structure):
                _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

            class RECT(ctypes.Structure):
                _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG),
                            ("right", wintypes.LONG), ("bottom", wintypes.LONG)]

            class MONITORINFO(ctypes.Structure):
                _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", RECT),
                            ("rcWork", RECT), ("dwFlags", wintypes.DWORD)]

            user32 = ctypes.windll.user32
            user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
            user32.MonitorFromWindow.restype = wintypes.HANDLE
            user32.MonitorFromPoint.argtypes = [POINT, wintypes.DWORD]
            user32.MonitorFromPoint.restype = wintypes.HANDLE
            user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MONITORINFO)]
            user32.GetMonitorInfoW.restype = wintypes.BOOL
            monitor = None
            if parent is not None:
                parent.update_idletasks()
                monitor = user32.MonitorFromWindow(parent.winfo_id(), 2)
            else:
                point = POINT()
                if user32.GetCursorPos(ctypes.byref(point)):
                    monitor = user32.MonitorFromPoint(point, 2)
            if monitor:
                info = MONITORINFO()
                info.cbSize = ctypes.sizeof(MONITORINFO)
                if user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
                    r = info.rcWork
                    return r.left, r.top, r.right, r.bottom
        except (AttributeError, OSError, ValueError):
            pass
    return 0, 0, window.winfo_screenwidth(), window.winfo_screenheight()


def center_window(window: tk.Misc, width: int, height: int,
                  parent: tk.Misc | None = None) -> None:
    """Fenstergröße setzen und sichtbar im relevanten Monitor zentrieren."""
    left, top, right, bottom = _work_area(window, parent)
    available_w, available_h = right - left, bottom - top
    width = min(width, available_w)
    height = min(height, available_h)
    if parent is not None:
        parent.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - width) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - height) // 2
    else:
        x = left + (available_w - width) // 2
        y = top + (available_h - height) // 2
    x = max(left, min(x, right - width))
    y = max(top, min(y, bottom - height))
    window.geometry(f"{width}x{height}+{x}+{y}")
