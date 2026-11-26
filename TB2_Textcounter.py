"""Read-only experimental Signum inventory counter."""
from __future__ import annotations
import os
import queue
import threading
from time import perf_counter
from collections import Counter
import webbrowser
from tb2.version import APP_VERSION
from tb2.build_identity import window_title, info_identity
from tb2.settings import load_folder, remember_folder, load_option, bind_option
from tb2.project_info import PROJECT_URL, MIT_LICENSE
from tb2.window_position import center_window
from tb2.changelog import changelog_for_version
from tb2.app_identity import configure_app_identity, apply_window_icon
APP_TITLE = 'Signum Textcounter'
INFO_TEXT = 'Zählt erkannte Schriftzeichen je Schriftart in TB2- und TBL-Dateien. Leerzeichen werden nicht gezählt. Schnell überspringt erkannte JPEG-Bereiche und kann Zeichen übersehen. Vollständig analysiert alle Bytes. Die Erkennung ist noch nicht vollständig. Quelldateien werden ausschließlich binär gelesen.'
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from tb2.muster import extract_counter_lines

SPACE_CODE = 0xFA

def format_number(value, decimals=0):
    """German display formatting, independent of the system locale."""
    return format(value, f",.{decimals}f").translate(str.maketrans(",.", ".,"))


def counter_lines(data, mode):
    if mode != "fast":
        return extract_counter_lines(data)
    from tb2.jpeg_fast import jpeg_ranges
    spans = jpeg_ranges(data)
    if not spans:
        return extract_counter_lines(data)
    lines, warnings = [], []
    previous = 0
    for begin, end in spans + [(len(data), len(data))]:
        if begin > previous:
            part_lines, part_warnings = extract_counter_lines(data[previous:begin])
            lines.extend(part_lines)
            warnings.extend(w for w in part_warnings if not w.startswith("Kein bekanntes Schriftformat gefunden:"))
        previous = max(previous, end)
    if not lines:
        warnings.append("Kein bekanntes Schriftformat gefunden: nicht als 0 Zeichen interpretieren.")
    return lines, warnings

def scan(root, recursive, stop, events, mode="fast"):
    counts = Counter()
    files = lines_total = uncertain = errors = 0
    paths = []
    def walk_error(exc):
        events.put(("error", str(exc)))
    try:
        for base, dirs, names in os.walk(root, followlinks=False, onerror=walk_error):
            if stop.is_set():
                return
            dirs[:] = [d for d in dirs if recursive and not os.path.islink(os.path.join(base,d))
                       and not getattr(os.path, "isjunction", lambda p: False)(os.path.join(base,d))]
            for name in names:
                if stop.is_set():
                    return
                path = Path(base) / name
                if path.suffix.lower() in (".tb2", ".tbl") and not path.is_symlink():
                    paths.append(path)
        total = len(paths)
        events.put(("discovered", total))
        for path in paths:
            if stop.is_set():
                return
            files += 1
            try:
                with path.open("rb") as source:
                    lines, warnings = counter_lines(source.read(), mode)
                lines_total += len(lines)
                if warnings or not lines:
                    uncertain += 1
                for font, glyphs in lines:
                    counts[font.upper()] += sum(c != SPACE_CODE for c in glyphs)
            except Exception as exc:
                errors += 1
                events.put(("error", f"{path}: {exc}"))
            if files == 1 or files % 10 == 0 or files == total:
                events.put(("progress", files, total))
    except Exception as exc:
        errors += 1
        events.put(("error", str(exc)))
    finally:
        events.put(("done", dict(counts), files, lines_total, uncertain, errors, stop.is_set()))

class App(tk.Tk):
    def __init__(self):
        configure_app_identity("ropaha.SignumTextcounter")
        super().__init__()
        apply_window_icon(self)
        self.title(window_title(APP_TITLE, APP_VERSION))
        center_window(self, 900, 560)
        self.minsize(720, 480)
        self.folder = tk.StringVar(value=load_folder())
        self.recursive = tk.BooleanVar(value=load_option("recursive", True))
        bind_option(self.recursive, "recursive")
        self.status = tk.StringVar(value="Bereit. Ordner auswählen und Zählung starten.")
        self.summary = tk.StringVar(value="Noch keine Ergebnisse.")
        self.events = queue.Queue()
        self.stop = threading.Event()
        self.running = False
        self.access_issues = []
        self.exit_after_scan = False
        self.protocol("WM_DELETE_WINDOW", self.request_exit)
        frame = ttk.Frame(self, padding=14)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Ordner:").grid(row=0, column=0, sticky="w")
        self.entry = ttk.Entry(frame, textvariable=self.folder)
        self.entry.grid(row=0, column=1, sticky="ew", padx=10)
        self.choose_button = ttk.Button(frame, text="Ordner wählen …", command=self.choose)
        self.choose_button.grid(row=0, column=2)
        self.check = ttk.Checkbutton(frame, text="Unterordner einbeziehen", variable=self.recursive)
        self.check.grid(row=1, column=1, sticky="w", pady=(10,2))
        self.search_mode_var = tk.StringVar(value=load_option("search_mode", "fast"))
        bind_option(self.search_mode_var, "search_mode")
        mode_options = ttk.Frame(frame)
        mode_options.grid(row=2, column=1, columnspan=2, sticky="w", pady=(4,2))
        ttk.Label(mode_options, text="Suchmodus:").pack(side="left", padx=(0,10))
        self.fast_radio = ttk.Radiobutton(mode_options, text="Schnell (JPEG überspringen)", variable=self.search_mode_var, value="fast")
        self.fast_radio.pack(side="left", padx=(0,14))
        self.full_radio = ttk.Radiobutton(mode_options, text="Vollständig (alle Bytes)", variable=self.search_mode_var, value="full")
        self.full_radio.pack(side="left")
        actions = ttk.Frame(frame)
        actions.grid(row=3, column=0, columnspan=3, sticky="w", pady=(12,10))
        self.button = ttk.Button(actions, text="Zählen", command=self.start, state="disabled")
        self.button.pack(side="left")
        self.clear_button = ttk.Button(actions, text="Leeren", command=self.clear, state="disabled")
        self.clear_button.pack(side="left", padx=8)
        self.issues_button = ttk.Button(actions, text="Zugriffsprobleme", command=self.show_access_issues, state="disabled")
        
        self.progress = ttk.Progressbar(frame, mode="determinate")
        self.progress.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(0,7))
        ttk.Label(frame, textvariable=self.status).grid(row=5, column=0, columnspan=3, sticky="w")
        ttk.Label(frame, textvariable=self.summary, wraplength=680).grid(row=6, column=0, columnspan=3, sticky="w", pady=(4,8))
        results = ttk.Frame(frame)
        results.grid(row=7, column=0, columnspan=3, sticky="nsew")
        results.columnconfigure(0, weight=1)
        results.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(results, columns=("font","count"), show="headings")
        self.result_counts = {}
        self.has_results = False
        self.sort_column = "count"
        self.sort_descending = True
        self.update_sort_headings()
        self.tree.column("font", width=450, anchor="w")
        self.tree.column("count", width=150, anchor="e", stretch=False)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(results, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)
        footer = ttk.Frame(frame)
        footer.grid(row=8, column=0, columnspan=3, sticky="ew", pady=(10,0))
        ttk.Button(footer, text="Programm beenden", command=self.request_exit).pack(side="right")
        ttk.Button(footer, text="Info", command=self.show_info).pack(side="right", padx=(0,8))
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(7, weight=1)
        self.folder.trace_add("write", self.update_button)
        self.update_button()
        self.after(100, self.poll)

    def choose(self):
        selected = filedialog.askdirectory(title="Ordner mit TB2-/TBL-Dateien auswählen", initialdir=self.folder.get() or None)
        if selected:
            self.folder.set(selected)
            remember_folder(selected)

    def update_button(self, *_):
        if not self.running:
            self.button.configure(state="normal" if self.folder.get().strip() else "disabled")

    def update_sort_headings(self):
        for column, label in (("font", "Schriftart"), ("count", "Zeichenanzahl")):
            arrow = (" ▼" if self.sort_descending else " ▲") if column == self.sort_column else ""
            self.tree.heading(column, text=label + arrow,
                              command=lambda col=column: self.sort_results(col))

    def sort_results(self, column):
        if self.running:
            return
        if column == self.sort_column:
            self.sort_descending = not self.sort_descending
        else:
            self.sort_column = column
            self.sort_descending = column == "count"
        self.update_sort_headings()
        self.render_results()

    def render_results(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        if not self.has_results:
            return
        rows = sorted(self.result_counts.items(), key=lambda x: x[0].casefold())
        if self.sort_column == "count":
            rows.sort(key=lambda x: x[1], reverse=self.sort_descending)
        elif self.sort_descending:
            rows.reverse()
        self.tree.insert("", "end", values=("GESAMT (erkannte Zeichen)",
                                             format_number(sum(self.result_counts.values()))))
        for font, count in rows:
            self.tree.insert("", "end", values=(font, format_number(count)))

    def clear(self):
        self.result_counts = {}
        self.has_results = False
        self.sort_column = "count"
        self.sort_descending = True
        self.update_sort_headings()
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.progress.configure(mode="determinate", value=0)
        self.summary.set("Noch keine Ergebnisse.")
        self.status.set("Bereit. Ordner auswählen und Zählung starten.")
        self.access_issues.clear()
        self.clear_button.configure(state="disabled")
        self.issues_button.pack_forget()

    def start(self):
        if self.running:
            self.stop.set()
            self.status.set("Abbruch angefordert …")
            return
        if not self.folder.get().strip() or not Path(self.folder.get()).is_dir():
            messagebox.showwarning("Ordner fehlt", "Bitte einen gültigen Ordner auswählen.", parent=self)
            return
        remember_folder(self.folder.get().strip())
        self.clear()
        self.started_at = perf_counter()
        self.running = True
        self.stop.clear()
        self.button.configure(text="Abbrechen")
        for widget in (self.entry, self.choose_button, self.check, self.fast_radio, self.full_radio):
            widget.configure(state="disabled")
        self.status.set("Dateien werden ermittelt …")
        self.progress.configure(mode="indeterminate", value=0)
        self.progress.start(12)
        threading.Thread(target=scan, args=(Path(self.folder.get()), self.recursive.get(), self.stop, self.events, self.search_mode_var.get()), daemon=True).start()

    def request_exit(self):
        if not self.running:
            self.destroy()
        elif messagebox.askyesno("Programm beenden", "Zählung abbrechen und Programm beenden?", parent=self):
            self.exit_after_scan = True
            self.stop.set()

    def poll(self):
        try:
            while True:
                event = self.events.get_nowait()
                if event[0] == "discovered":
                    total = event[1]
                    self.progress.stop()
                    self.progress.configure(mode="determinate", maximum=max(total, 1), value=0)
                    if not self.stop.is_set():
                        self.status.set(f"{format_number(total)} Dateien ermittelt. Zählung läuft …")
                elif event[0] == "progress":
                    _, current, total = event
                    self.progress.configure(value=current)
                    if not self.stop.is_set():
                        self.status.set(f"{format_number(current)} von {format_number(total)} Dateien analysiert ({format_number(100 * current / total, 1)} %)")
                elif event[0] == "error":
                    self.access_issues.append(event[1])
                elif event[0] == "done":
                    _, counts, files, lines, uncertain, errors, cancelled = event
                    if self.exit_after_scan:
                        self.destroy()
                        return
                    elapsed = perf_counter() - self.started_at
                    duration = format_number(elapsed, 2)
                    total = sum(counts.values())
                    self.result_counts = counts
                    self.has_results = True
                    self.render_results()
                    self.status.set(f"{'Abgebrochen' if cancelled else 'Fertig'}: {format_number(files)} Dateien | {format_number(len(counts))} Schriftarten | {format_number(total)} Zeichen | Dauer: {duration} s")
                    self.summary.set(f"{format_number(lines)} erkannte Zeilen | {format_number(uncertain)} unsichere Dateien | {format_number(errors)} Dateifehler | {format_number(len(self.access_issues))} Fehlermeldungen. Ergebnis möglicherweise unvollständig.")
                    self.running = False
                    self.progress.stop()
                    self.progress.configure(mode="determinate", value=files)
                    self.button.configure(text="Zählen")
                    self.clear_button.configure(state="normal")
                    if self.access_issues:
                        self.issues_button.configure(state="normal")
                        self.issues_button.pack(side="left")
                    else:
                        self.issues_button.pack_forget()
                    for widget in (self.entry, self.choose_button, self.check, self.fast_radio, self.full_radio):
                        widget.configure(state="normal")
                    self.update_button()
        except queue.Empty:
            pass
        self.after(100, self.poll)

    def show_info(self):
        """Show application details and the former footer help text."""
        dialog = tk.Toplevel(self)
        dialog.title("Info – Signum Textcounter")
        center_window(dialog, 650, 380, parent=self)
        dialog.minsize(480, 300)
        dialog.transient(self)
        body = ttk.Frame(dialog, padding=18)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text=f"{APP_TITLE} – Version {APP_VERSION}",
                  font=("TkDefaultFont", 13, "bold")).pack(anchor="w", pady=(0, 12))
        ttk.Label(body, text=info_identity(), wraplength=580).pack(anchor="w", pady=(0, 8))
        help_frame = ttk.Frame(body)
        help_frame.pack(fill="both", expand=True)
        help_text = tk.Text(help_frame, wrap="word", height=9, relief="flat",
                            font=("TkDefaultFont", 10),
                            background=dialog.cget("background"), padx=2, pady=2)
        help_text.insert("1.0", INFO_TEXT)
        help_text.configure(state="disabled")
        help_text.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(help_frame, orient="vertical", command=help_text.yview)
        scrollbar.pack(side="right", fill="y")
        help_text.configure(yscrollcommand=scrollbar.set)
        buttons = ttk.Frame(body)
        buttons.pack(fill="x", pady=(14, 0))
        ttk.Button(buttons, text="Was ist neu?",
                   command=lambda: self.show_changelog(dialog)).pack(side="left")
        ttk.Button(buttons, text="GitHub",
                   command=lambda: webbrowser.open(PROJECT_URL)).pack(side="left", padx=(8, 0))
        ttk.Button(buttons, text="MIT-Lizenz",
                   command=lambda: self.show_license(dialog)).pack(side="left", padx=(8, 0))
        ttk.Button(buttons, text="Schließen", command=dialog.destroy).pack(side="right")

    def show_changelog(self, parent):
        """Display the bundled version history, including this installed version."""
        dialog = tk.Toplevel(parent)
        dialog.title(f"Was ist neu? – Signum Textcounter {APP_VERSION}")
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

    def show_license(self, parent):
        """Display the complete license bundled with this program."""
        dialog = tk.Toplevel(parent)
        dialog.title("MIT-Lizenz – Signum Textcounter")
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

    def show_access_issues(self):
        if not self.access_issues:
            return
        dialog = tk.Toplevel(self)
        dialog.title("Zugriffsprobleme – Signum Textcounter")
        center_window(dialog, 780, 500, parent=self)
        dialog.minsize(480, 300)
        dialog.transient(self)
        body = ttk.Frame(dialog, padding=14)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text=f"{format_number(len(self.access_issues))} Zugriffs- und Lesefehler",
                  font=("TkDefaultFont", 12, "bold")).pack(anchor="w", pady=(0, 10))
        text_frame = ttk.Frame(body)
        text_frame.pack(fill="both", expand=True)
        details = tk.Text(text_frame, wrap="word", font=("TkDefaultFont", 10), padx=8, pady=8)
        details.insert("1.0", "\n\n".join(self.access_issues))
        details.configure(state="disabled")
        details.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=details.yview)
        scrollbar.pack(side="right", fill="y")
        details.configure(yscrollcommand=scrollbar.set)
        ttk.Button(body, text="Schließen", command=dialog.destroy).pack(anchor="e", pady=(10, 0))


if __name__ == "__main__":
    App().mainloop()
