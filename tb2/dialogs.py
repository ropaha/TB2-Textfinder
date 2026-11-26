"""Shared non-modal application dialogs."""
import tkinter as tk
from tkinter import ttk
import webbrowser
from tb2.version import APP_VERSION
from tb2.build_identity import info_identity
from tb2.project_info import PROJECT_URL, MIT_LICENSE
from tb2.window_position import center_window
from tb2.changelog import changelog_for_version
from tb2.formatting import format_number


def show_info(parent, app_title, help_content, *, compact=False):
    """Show application details and the former footer help text."""
    dialog = tk.Toplevel(parent)
    dialog.title(f"Info – {app_title}")
    center_window(dialog, 650, 380, parent=parent)
    if not compact:
        dialog.minsize(480, 300)
    dialog.transient(parent)
    body = ttk.Frame(dialog, padding=18)
    body.pack(fill="both", expand=True)
    ttk.Label(body, text=f"{app_title} – Version {APP_VERSION}",
              font=("TkDefaultFont", 13, "bold")).pack(anchor="w", pady=(0, 12))
    ttk.Label(body, text=info_identity(), wraplength=580).pack(anchor="w", pady=(0, 8))
    if compact:
        ttk.Label(body, text=help_content, wraplength=590).pack(anchor="w")
        buttons = ttk.Frame(body)
        buttons.pack(side="bottom", fill="x")
        ttk.Button(buttons, text="GitHub", command=lambda: webbrowser.open(PROJECT_URL)).pack(side="left")
        ttk.Button(buttons, text="MIT-Lizenz", command=lambda: show_license(dialog, app_title)).pack(side="left", padx=8)
        ttk.Button(buttons, text="Schließen", command=dialog.destroy).pack(side="right")
        return
    help_frame = ttk.Frame(body)
    help_frame.pack(fill="both", expand=True)
    help_text = tk.Text(help_frame, wrap="word", height=9, relief="flat",
                        font=("TkDefaultFont", 10),
                        background=dialog.cget("background"), padx=2, pady=2)
    help_text.insert("1.0", help_content)
    help_text.configure(state="disabled")
    help_text.pack(side="left", fill="both", expand=True)
    scrollbar = ttk.Scrollbar(help_frame, orient="vertical", command=help_text.yview)
    scrollbar.pack(side="right", fill="y")
    help_text.configure(yscrollcommand=scrollbar.set)
    buttons = ttk.Frame(body)
    buttons.pack(fill="x", pady=(14, 0))
    ttk.Button(buttons, text="Was ist neu?",
               command=lambda: show_changelog(dialog, app_title)).pack(side="left")
    ttk.Button(buttons, text="GitHub",
               command=lambda: webbrowser.open(PROJECT_URL)).pack(side="left", padx=(8, 0))
    ttk.Button(buttons, text="MIT-Lizenz",
               command=lambda: show_license(dialog, app_title)).pack(side="left", padx=(8, 0))
    ttk.Button(buttons, text="Schließen", command=dialog.destroy).pack(side="right")

def show_changelog(parent, app_title):
    """Display the bundled version history, including this installed version."""
    dialog = tk.Toplevel(parent)
    dialog.title(f"Was ist neu? – {app_title} {APP_VERSION}")
    center_window(dialog, 720, 500, parent=parent)
    dialog.minsize(450, 320)
    dialog.transient(parent)
    body = ttk.Frame(dialog, padding=14)
    body.pack(fill="both", expand=True)
    ttk.Label(body, text=f"Versionsverlauf bis {APP_VERSION}",
              font=("TkDefaultFont", 12, "bold")).pack(anchor="w", pady=(0, 10))
    text_frame = ttk.Frame(body)
    text_frame.pack(fill="both", expand=True)
    history = tk.Text(text_frame, wrap="word", font=("TkDefaultFont", 10), padx=8, pady=8)
    history.insert("1.0", changelog_for_version(APP_VERSION))
    history.configure(state="disabled")
    history.pack(side="left", fill="both", expand=True)
    scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=history.yview)
    scrollbar.pack(side="right", fill="y")
    history.configure(yscrollcommand=scrollbar.set)
    ttk.Button(body, text="Schließen", command=dialog.destroy).pack(anchor="e", pady=(10, 0))

def show_license(parent, app_title):
    """Display the complete license bundled with this program."""
    dialog = tk.Toplevel(parent)
    dialog.title(f"MIT-Lizenz – {app_title}")
    center_window(dialog, 720, 450, parent=parent)
    dialog.minsize(450, 300)
    dialog.transient(parent)
    body = ttk.Frame(dialog, padding=14)
    body.pack(fill="both", expand=True)
    text_frame = ttk.Frame(body)
    text_frame.pack(fill="both", expand=True)
    license_text = tk.Text(text_frame, wrap="word", font=("TkDefaultFont", 10))
    license_text.insert("1.0", MIT_LICENSE)
    license_text.configure(state="disabled")
    license_text.pack(side="left", fill="both", expand=True)
    scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=license_text.yview)
    scrollbar.pack(side="right", fill="y")
    license_text.configure(yscrollcommand=scrollbar.set)
    ttk.Button(body, text="Schließen", command=dialog.destroy).pack(anchor="e", pady=(10, 0))

def show_access_issues(parent, app_title, issues, description):
    if not issues:
        return
    dialog = tk.Toplevel(parent)
    dialog.title(f"Zugriffsprobleme – {app_title}")
    center_window(dialog, 780, 500, parent=parent)
    dialog.minsize(480, 300)
    dialog.transient(parent)
    body = ttk.Frame(dialog, padding=14)
    body.pack(fill="both", expand=True)
    ttk.Label(body, text=f"{format_number(len(issues))} {description}",
              font=("TkDefaultFont", 12, "bold")).pack(anchor="w", pady=(0, 10))
    text_frame = ttk.Frame(body)
    text_frame.pack(fill="both", expand=True)
    details = tk.Text(text_frame, wrap="word", font=("TkDefaultFont", 10), padx=8, pady=8)
    details.insert("1.0", "\n\n".join(issues))
    details.configure(state="disabled")
    details.pack(side="left", fill="both", expand=True)
    scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=details.yview)
    scrollbar.pack(side="right", fill="y")
    details.configure(yscrollcommand=scrollbar.set)
    ttk.Button(body, text="Schließen", command=dialog.destroy).pack(anchor="e", pady=(10, 0))

