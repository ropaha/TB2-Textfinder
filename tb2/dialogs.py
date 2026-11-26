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

def show_changelog(parent, parent):
    """Display the bundled version history, including this installed version."""
    dialog = tk.Toplevel(parent)
    dialog.title(f"Was ist neu? – TB2-Textfinder {APP_VERSION}")
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

def show_license(parent, parent):
    """Display the complete license bundled with this program."""
    dialog = tk.Toplevel(parent)
    dialog.title("MIT-Lizenz – TB2-Textfinder")
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

def show_access_issues(parent):
    if not parent.access_issues:
        return
    dialog = tk.Toplevel(parent)
    dialog.title("Zugriffsprobleme – TB2-Textfinder")
    center_window(dialog, 780, 500, parent=parent)
    dialog.minsize(480, 300)
    dialog.transient(parent)
    body = ttk.Frame(dialog, padding=14)
    body.pack(fill="both", expand=True)
    ttk.Label(body, text=f"{format_number(len(parent.access_issues))} übersprungene Verzeichnisse",
              font=("TkDefaultFont", 12, "bold")).pack(anchor="w", pady=(0, 10))
    text_frame = ttk.Frame(body)
    text_frame.pack(fill="both", expand=True)
    details = tk.Text(text_frame, wrap="word", font=("TkDefaultFont", 10), padx=8, pady=8)
    details.insert("1.0", "\n\n".join(parent.access_issues))
    details.configure(state="disabled")
    details.pack(side="left", fill="both", expand=True)
    scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=details.yview)
    scrollbar.pack(side="right", fill="y")
    details.configure(yscrollcommand=scrollbar.set)
    ttk.Button(body, text="Schließen", command=dialog.destroy).pack(anchor="e", pady=(10, 0))

def choose_folder(parent):
    folder = filedialog.askdirectory(title="Ordner mit TB2-/TBL-Dateien auswählen", initialdir=parent.folder_var.get() or None)
    if folder:
        parent.folder_var.set(folder)
        remember_folder(folder)

def _update_search_button(parent, *_args):
    """Suche nur mit eingetragenem Ordner starten; Abbruchmodus bewahren."""
    if not parent.scanning:
        parent.search_button.configure(
            state="normal" if parent.folder_var.get().strip() and parent.term_var.get().strip() else "disabled",
            text="Suchen")

def request_exit(parent):
    """Während einer Prüfung Rückfrage stellen und kontrolliert beenden."""
    if not parent.scanning:
        parent.destroy()
        return
    if parent.exit_after_scan:
        return
    if not messagebox.askyesno(
            "Programm beenden",
            "Sind Sie sicher, dass Sie die Suche abbrechen und das Programm beenden möchten?",
            parent=parent):
        return
    parent.exit_after_scan = True
    parent.cancel_scan_event.set()
    parent.search_button.configure(state="disabled", text="Abbruch läuft …")
    parent.status_var.set("Programm wird nach Abbruch der laufenden Arbeit beendet …")

def search_or_cancel(parent):
    """Start a scan, or request cooperative cancellation."""
    if parent.scanning:
        if not parent.cancel_scan_event.is_set():
            parent.cancel_scan_event.set()
            parent.search_button.configure(state="disabled", text="Abbruch läuft …")
            parent.status_var.set("Abbruch angefordert – laufender Verzeichniszugriff bzw. aktuelle Datei wird abgeschlossen …")
        return
    parent.start_scan()

def _set_inputs_locked(parent, locked):
    for widget in (parent.term_entry, parent.folder_entry, parent.folder_button, parent.recursive_check, parent.whole_check, parent.case_check, parent.fast_radio, parent.full_radio):
        widget.configure(state="disabled" if locked else "normal")

def start_scan(parent):
    folder_text = parent.folder_var.get().strip()
    term = parent.term_var.get().strip()
    if not folder_text or not Path(folder_text).is_dir():
        messagebox.showwarning("Ordner fehlt", "Bitte einen gültigen Ordner auswählen.")
        return
    if not term:
        messagebox.showwarning("Suchtext fehlt", "Bitte einen Suchtext eingeben.")
        return
    if parent.scanning:
        return
    remember_folder(folder_text)
    parent.cancel_scan_event.clear()
    parent.scanning = True
    parent._set_inputs_locked(True)
    parent.result_paths = []
    parent.access_issues = []
    parent.issues_button.pack_forget()
    parent.search_button.configure(state="normal", text="Suche abbrechen")
    parent.clear_button.configure(state="disabled")
    parent.copy_button.configure(state="disabled")
    parent.open_button.configure(state="disabled")
    parent.save_button.configure(state="disabled")
    for item in parent.tree.get_children():
        parent.tree.delete(item)
    parent._fit_path_column([])
    parent.progress.configure(mode="indeterminate", value=0)
    parent.progress.start(12)
    parent.summary_var.set("Suche läuft – Ergebnis folgt nach Abschluss oder Abbruch.")
    parent.status_var.set("Durchsuche Verzeichnisstruktur nach TB2-/TBL-Dateien …")
    threading.Thread(
        target=parent._discover_and_scan,
        args=(Path(folder_text), parent.recursive_var.get(), term,
              parent.case_var.get(), parent.search_mode_var.get(), parent.whole_word_var.get()),
        daemon=True,
    ).start()

def _discover_and_scan(parent, root: Path, recursive: bool, term: str,
                       case_sensitive: bool, mode: str, whole_word: bool):
    files = []
    skipped = []
    directories_checked = 0

    def on_walk_error(exc):
        skipped.append(f"{exc.filename or 'Unbekannter Ordner'}: {exc}")

    try:
        if recursive:
            directories = os.walk(root, topdown=True, followlinks=False,
                                  onerror=on_walk_error)
        else:
            def one_directory():
                try:
                    with os.scandir(root) as entries:
                        yield str(root), [], [entry.name for entry in entries
                                               if entry.is_file(follow_symlinks=False)]
                except OSError as exc:
                    on_walk_error(exc)
            directories = one_directory()

        for directory, subdirs, names in directories:
            if parent.cancel_scan_event.is_set():
                break
            directories_checked += 1
            if recursive:
                subdirs[:] = [name for name in subdirs
                              if not getattr(os.path, "isjunction", lambda p: False)(os.path.join(directory, name))]
            for name in names:
                if name.lower().endswith((".tb2", ".tbl")):
                    files.append(Path(directory) / name)
            if directories_checked % 50 == 0:
                parent.events.put(("discovery", directories_checked, len(files)))
        parent.events.put(("discovery_done", len(files), directories_checked, skipped))
        if parent.cancel_scan_event.is_set() or not files:
            parent.events.put(("finished", [], len(files), 0, mode, 0.0, 0,
                             parent.cancel_scan_event.is_set()))
            return
        parent._scan_worker(files, term, case_sensitive, mode, whole_word)
    except Exception as exc:
        parent.events.put(("worker_error", str(exc)))

def _scan_worker(parent, files: list[Path], term: str, case_sensitive: bool, mode: str, whole_word: bool):
    found: list[str] = []
    errors = 0
    started = perf_counter()
    processed = 0
    for index, path in enumerate(files, start=1):
        if parent.cancel_scan_event.is_set():
            break
        if mode == "fast":
            try:
                from tb2.jpeg_fast import contains_term_fast
                data = mask_resource_paths(path.read_bytes())
                # Zweistufige Ganzwortsuche: Nur Kandidaten mit einem
                # Teilworttreffer benötigen die teure Wortgrenzenprüfung.
                # JPEG-Bereiche werden in beiden Stufen identisch behandelt.
                candidate = contains_term_fast(data, term, case_sensitive)
                if whole_word and candidate:
                    from tb2.jpeg_fast import jpeg_ranges
                    spans = jpeg_ranges(data)
                    previous = 0
                    hit = False
                    for begin, end in spans:
                        if begin > previous and contains_whole_word(data[previous:begin], term, case_sensitive):
                            hit = True
                            break
                        previous = max(previous, end)
                    if not hit and previous < len(data):
                        hit = contains_whole_word(data[previous:], term, case_sensitive)
                else:
                    hit = candidate
                error = None
            except (OSError, ValueError, MemoryError) as exc:
                hit, error = False, str(exc)
        else:
            hit, error = scan_file(path, term, case_sensitive, whole_word)
        if hit:
            found.append(str(path.resolve()))
        if error:
            errors += 1
        processed = index
        parent.events.put(("progress", index, len(files), path.name))
    parent.events.put(("finished", found, len(files), errors, mode, perf_counter() - started,
                     processed, parent.cancel_scan_event.is_set()))

def _poll_events(parent):
    try:
        while True:
            event = parent.events.get_nowait()
            if event[0] == "discovery":
                _, directories, found = event
                if not parent.cancel_scan_event.is_set():
                    parent.status_var.set(
                        f"Durchsuche Verzeichnisse: {format_number(directories)} Ordner, "
                        f"{format_number(found)} TB2-/TBL-Datei(en) gefunden …")
            elif event[0] == "discovery_done":
                _, total, directories, skipped = event
                parent.access_issues = skipped
                parent.progress.stop()
                parent.progress.configure(mode="determinate", maximum=max(total, 1), value=0)
                if not parent.cancel_scan_event.is_set():
                    parent.status_var.set(
                        f"Dateisuche abgeschlossen: {format_number(directories)} Ordner, "
                        f"{format_number(total)} TB2-/TBL-Datei(en). Suche läuft …")
            elif event[0] == "progress":
                _, current, total, filename = event
                parent.progress.configure(value=current)
                if not parent.cancel_scan_event.is_set():
                    parent.status_var.set(f"Datei {format_number(current)}/{format_number(total)}: {filename}")
            elif event[0] == "finished":
                if parent.exit_after_scan:
                    parent.destroy()
                    return
                _, found, total, errors, mode, seconds, processed, cancelled = event
                parent.progress.stop()
                parent.result_paths = found
                for index, path in enumerate(found):
                    parent.tree.insert("", "end", values=(path,), tags=row_tags(index))
                parent._fit_path_column(found)
                parent.scanning = False
                parent._set_inputs_locked(False)
                parent._update_search_button()
                parent.clear_button.configure(state="normal" if found else "disabled")
                state = "normal" if found else "disabled"
                parent.copy_button.configure(state=state)
                parent.save_button.configure(state=state)
                # Die Datei-Öffnen-Schaltfläche wird erst nach Auswahl eines Treffers aktiviert.
                parent.open_button.configure(state="disabled")
                if cancelled:
                    msg = (f"Abgebrochen ({'Schnell' if mode == 'fast' else 'Vollständig'}): "
                           f"{format_number(processed)}/{format_number(total)} Dateien geprüft, {format_number(len(found))} Treffer – {format_number(seconds, 2)} s.")
                else:
                    msg = f"Fertig ({'Schnell' if mode == 'fast' else 'Vollständig'}): {format_number(len(found))} Treffer in {format_number(total)} Datei(en) – {format_number(seconds, 2)} s."
                if errors:
                    msg += f" {format_number(errors)} Datei(en) konnten nicht gelesen werden."
                parent.summary_var.set(msg)
                parent.status_var.set("Suche abgebrochen." if cancelled else "Suche abgeschlossen.")
                if not cancelled and not total:
                    parent.status_var.set("Keine TB2-/TBL-Dateien gefunden.")
                if parent.access_issues:
                    parent.issues_button.configure(
                        text=f"Zugriffsprobleme ({format_number(len(parent.access_issues))})")
                    parent.issues_button.pack(side="left", padx=(8, 0), after=parent.search_button)
            elif event[0] == "worker_error":
                if parent.exit_after_scan:
                    parent.destroy()
                    return
                parent.progress.stop()
                parent.scanning = False
                parent._set_inputs_locked(False)
                parent._update_search_button()
                parent.status_var.set("Suche fehlgeschlagen.")
                parent.summary_var.set("Keine Ergebnisse – Suche fehlgeschlagen.")
                messagebox.showerror("Suche fehlgeschlagen", event[1])
    except queue.Empty:
        pass
    parent.after(100, parent._poll_events)

def _fit_path_column(parent, paths=None):
    """Spaltenbreite an den längsten sichtbaren Dateipfad anpassen."""
    if paths is None:
        paths = parent.result_paths
    style = ttk.Style(parent)
    font_name = style.lookup("Treeview", "font") or "TkDefaultFont"
    font = tkfont.nametofont(font_name) if font_name in tkfont.names(parent) else tkfont.nametofont("TkDefaultFont")
    heading_width = font.measure("Dateipfad") + 32
    content_width = max((font.measure(path) for path in paths), default=0) + 24
    # Feste Spaltenbreite: manuelle Änderungen bleiben erhalten;
    # lange Pfade können horizontal gescrollt werden.
    parent.tree.column("path", width=max(heading_width, content_width, 80))

def _update_open_button_state(parent, _event=None):
    """Enable 'Datei öffnen' only when one result is selected."""
    selected = parent.tree.selection()
    state = "normal" if len(selected) == 1 else "disabled"
    parent.open_button.configure(state=state)

def open_selected_file(parent):
    """Open the selected result using the Windows file association."""
    selected = parent.tree.selection()
    if len(selected) != 1:
        messagebox.showinfo(
            "Datei auswählen",
            "Bitte zuerst eine Datei in der Trefferliste markieren.",
        )
        return

    values = parent.tree.item(selected[0], "values")
    if values:
        parent._open_file_path(str(values[0]))

def open_result_file(parent, event):
    """Open the double-clicked result using Windows file associations."""
    row_id = parent.tree.identify_row(event.y)
    if not row_id:
        return

    values = parent.tree.item(row_id, "values")
    if values:
        parent._open_file_path(str(values[0]))

def _open_file_path(parent, file_path: str):
    """Open a TB2 file through the normal Windows file association."""
    if not Path(file_path).is_file():
        messagebox.showerror(
            "Datei nicht gefunden",
            f"Die gefundene Datei ist nicht mehr vorhanden oder nicht erreichbar:\n\n{file_path}",
        )
        return

    try:
        if not hasattr(os, "startfile"):
            messagebox.showerror(
                "Nur unter Windows verfügbar",
                "Das Öffnen über die Dateizuordnung ist nur unter Windows verfügbar.",
            )
            return
        # os.startfile nutzt die Windows-Dateizuordnung, genau wie ein Doppelklick
        # auf die Datei im Explorer.
        os.startfile(file_path)
        parent.status_var.set(f"Datei geöffnet: {file_path}")
    except OSError as exc:
        messagebox.showerror(
            "Datei konnte nicht geöffnet werden",
            "Windows konnte für diese TB2-Datei keine passende Anwendung starten. "
            "Prüfe bitte die Dateizuordnung.\n\n"
            f"Datei: {file_path}\n\nFehler: {exc}",
        )

def copy_paths(parent):
    if not parent.result_paths:
        return
    parent.clipboard_clear()
    parent.clipboard_append("\n".join(parent.result_paths))
    parent.status_var.set(f"{format_number(len(parent.result_paths))} Pfad/Pfade in die Zwischenablage kopiert.")

def save_paths(parent):
    if not parent.result_paths:
        return
    destination = filedialog.asksaveasfilename(
        title="Trefferpfade speichern",
        defaultextension=".txt",
        filetypes=[("Textdatei", "*.txt"), ("Alle Dateien", "*.*")],
        initialfile="TB2_Treffer.txt",
        initialdir=load_export_folder() or None,
    )
    if not destination:
        return
    try:
        Path(destination).write_text("\n".join(parent.result_paths) + "\n", encoding="utf-8")
    except OSError as exc:
        messagebox.showerror("Speichern fehlgeschlagen", str(exc))
        return
    remember_export_folder(Path(destination).resolve().parent)
    parent.status_var.set(f"Pfadliste gespeichert: {destination}")

def clear_results(parent):
    if parent.scanning:
        return
    parent.result_paths = []
    parent.access_issues = []
    parent.issues_button.pack_forget()
    parent.clear_button.configure(state="disabled")
    for item in parent.tree.get_children():
        parent.tree.delete(item)
    parent.copy_button.configure(state="disabled")
    parent.open_button.configure(state="disabled")
    parent.save_button.configure(state="disabled")
    parent._fit_path_column([])
    parent.status_var.set("Ergebnisliste geleert.")
    parent.summary_var.set("Noch keine Suche abgeschlossen.")

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

def show_license(self, parent):
    """Display the complete license bundled with this program."""
    dialog = tk.Toplevel(parent)
    dialog.title("MIT-Lizenz – TB2-Textfinder")
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
    dialog.title("Zugriffsprobleme – TB2-Textfinder")
    center_window(dialog, 780, 500, parent=self)
    dialog.minsize(480, 300)
    dialog.transient(self)
    body = ttk.Frame(dialog, padding=14)
    body.pack(fill="both", expand=True)
    ttk.Label(body, text=f"{format_number(len(self.access_issues))} übersprungene Verzeichnisse",
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

def choose_folder(self):
    folder = filedialog.askdirectory(title="Ordner mit TB2-/TBL-Dateien auswählen", initialdir=self.folder_var.get() or None)
    if folder:
        self.folder_var.set(folder)
        remember_folder(folder)

def _update_search_button(self, *_args):
    """Suche nur mit eingetragenem Ordner starten; Abbruchmodus bewahren."""
    if not self.scanning:
        self.search_button.configure(
            state="normal" if self.folder_var.get().strip() and self.term_var.get().strip() else "disabled",
            text="Suchen")

def request_exit(self):
    """Während einer Prüfung Rückfrage stellen und kontrolliert beenden."""
    if not self.scanning:
        self.destroy()
        return
    if self.exit_after_scan:
        return
    if not messagebox.askyesno(
            "Programm beenden",
            "Sind Sie sicher, dass Sie die Suche abbrechen und das Programm beenden möchten?",
            parent=self):
        return
    self.exit_after_scan = True
    self.cancel_scan_event.set()
    self.search_button.configure(state="disabled", text="Abbruch läuft …")
    self.status_var.set("Programm wird nach Abbruch der laufenden Arbeit beendet …")

def search_or_cancel(self):
    """Start a scan, or request cooperative cancellation."""
    if self.scanning:
        if not self.cancel_scan_event.is_set():
            self.cancel_scan_event.set()
            self.search_button.configure(state="disabled", text="Abbruch läuft …")
            self.status_var.set("Abbruch angefordert – laufender Verzeichniszugriff bzw. aktuelle Datei wird abgeschlossen …")
        return
    self.start_scan()

def _set_inputs_locked(self, locked):
    for widget in (self.term_entry, self.folder_entry, self.folder_button, self.recursive_check, self.whole_check, self.case_check, self.fast_radio, self.full_radio):
        widget.configure(state="disabled" if locked else "normal")

def start_scan(self):
    folder_text = self.folder_var.get().strip()
    term = self.term_var.get().strip()
    if not folder_text or not Path(folder_text).is_dir():
        messagebox.showwarning("Ordner fehlt", "Bitte einen gültigen Ordner auswählen.")
        return
    if not term:
        messagebox.showwarning("Suchtext fehlt", "Bitte einen Suchtext eingeben.")
        return
    if self.scanning:
        return
    remember_folder(folder_text)
    self.cancel_scan_event.clear()
    self.scanning = True
    self._set_inputs_locked(True)
    self.result_paths = []
    self.access_issues = []
    self.issues_button.pack_forget()
    self.search_button.configure(state="normal", text="Suche abbrechen")
    self.clear_button.configure(state="disabled")
    self.copy_button.configure(state="disabled")
    self.open_button.configure(state="disabled")
    self.save_button.configure(state="disabled")
    for item in self.tree.get_children():
        self.tree.delete(item)
    self._fit_path_column([])
    self.progress.configure(mode="indeterminate", value=0)
    self.progress.start(12)
    self.summary_var.set("Suche läuft – Ergebnis folgt nach Abschluss oder Abbruch.")
    self.status_var.set("Durchsuche Verzeichnisstruktur nach TB2-/TBL-Dateien …")
    threading.Thread(
        target=self._discover_and_scan,
        args=(Path(folder_text), self.recursive_var.get(), term,
              self.case_var.get(), self.search_mode_var.get(), self.whole_word_var.get()),
        daemon=True,
    ).start()

def _discover_and_scan(self, root: Path, recursive: bool, term: str,
                       case_sensitive: bool, mode: str, whole_word: bool):
    files = []
    skipped = []
    directories_checked = 0

    def on_walk_error(exc):
        skipped.append(f"{exc.filename or 'Unbekannter Ordner'}: {exc}")

    try:
        if recursive:
            directories = os.walk(root, topdown=True, followlinks=False,
                                  onerror=on_walk_error)
        else:
            def one_directory():
                try:
                    with os.scandir(root) as entries:
                        yield str(root), [], [entry.name for entry in entries
                                               if entry.is_file(follow_symlinks=False)]
                except OSError as exc:
                    on_walk_error(exc)
            directories = one_directory()

        for directory, subdirs, names in directories:
            if self.cancel_scan_event.is_set():
                break
            directories_checked += 1
            if recursive:
                subdirs[:] = [name for name in subdirs
                              if not getattr(os.path, "isjunction", lambda p: False)(os.path.join(directory, name))]
            for name in names:
                if name.lower().endswith((".tb2", ".tbl")):
                    files.append(Path(directory) / name)
            if directories_checked % 50 == 0:
                self.events.put(("discovery", directories_checked, len(files)))
        self.events.put(("discovery_done", len(files), directories_checked, skipped))
        if self.cancel_scan_event.is_set() or not files:
            self.events.put(("finished", [], len(files), 0, mode, 0.0, 0,
                             self.cancel_scan_event.is_set()))
            return
        self._scan_worker(files, term, case_sensitive, mode, whole_word)
    except Exception as exc:
        self.events.put(("worker_error", str(exc)))

def _scan_worker(self, files: list[Path], term: str, case_sensitive: bool, mode: str, whole_word: bool):
    found: list[str] = []
    errors = 0
    started = perf_counter()
    processed = 0
    for index, path in enumerate(files, start=1):
        if self.cancel_scan_event.is_set():
            break
        if mode == "fast":
            try:
                from tb2.jpeg_fast import contains_term_fast
                data = mask_resource_paths(path.read_bytes())
                # Zweistufige Ganzwortsuche: Nur Kandidaten mit einem
                # Teilworttreffer benötigen die teure Wortgrenzenprüfung.
                # JPEG-Bereiche werden in beiden Stufen identisch behandelt.
                candidate = contains_term_fast(data, term, case_sensitive)
                if whole_word and candidate:
                    from tb2.jpeg_fast import jpeg_ranges
                    spans = jpeg_ranges(data)
                    previous = 0
                    hit = False
                    for begin, end in spans:
                        if begin > previous and contains_whole_word(data[previous:begin], term, case_sensitive):
                            hit = True
                            break
                        previous = max(previous, end)
                    if not hit and previous < len(data):
                        hit = contains_whole_word(data[previous:], term, case_sensitive)
                else:
                    hit = candidate
                error = None
            except (OSError, ValueError, MemoryError) as exc:
                hit, error = False, str(exc)
        else:
            hit, error = scan_file(path, term, case_sensitive, whole_word)
        if hit:
            found.append(str(path.resolve()))
        if error:
            errors += 1
        processed = index
        self.events.put(("progress", index, len(files), path.name))
    self.events.put(("finished", found, len(files), errors, mode, perf_counter() - started,
                     processed, self.cancel_scan_event.is_set()))

def _poll_events(self):
    try:
        while True:
            event = self.events.get_nowait()
            if event[0] == "discovery":
                _, directories, found = event
                if not self.cancel_scan_event.is_set():
                    self.status_var.set(
                        f"Durchsuche Verzeichnisse: {format_number(directories)} Ordner, "
                        f"{format_number(found)} TB2-/TBL-Datei(en) gefunden …")
            elif event[0] == "discovery_done":
                _, total, directories, skipped = event
                self.access_issues = skipped
                self.progress.stop()
                self.progress.configure(mode="determinate", maximum=max(total, 1), value=0)
                if not self.cancel_scan_event.is_set():
                    self.status_var.set(
                        f"Dateisuche abgeschlossen: {format_number(directories)} Ordner, "
                        f"{format_number(total)} TB2-/TBL-Datei(en). Suche läuft …")
            elif event[0] == "progress":
                _, current, total, filename = event
                self.progress.configure(value=current)
                if not self.cancel_scan_event.is_set():
                    self.status_var.set(f"Datei {format_number(current)}/{format_number(total)}: {filename}")
            elif event[0] == "finished":
                if self.exit_after_scan:
                    self.destroy()
                    return
                _, found, total, errors, mode, seconds, processed, cancelled = event
                self.progress.stop()
                self.result_paths = found
                for index, path in enumerate(found):
                    self.tree.insert("", "end", values=(path,), tags=row_tags(index))
                self._fit_path_column(found)
                self.scanning = False
                self._set_inputs_locked(False)
                self._update_search_button()
                self.clear_button.configure(state="normal" if found else "disabled")
                state = "normal" if found else "disabled"
                self.copy_button.configure(state=state)
                self.save_button.configure(state=state)
                # Die Datei-Öffnen-Schaltfläche wird erst nach Auswahl eines Treffers aktiviert.
                self.open_button.configure(state="disabled")
                if cancelled:
                    msg = (f"Abgebrochen ({'Schnell' if mode == 'fast' else 'Vollständig'}): "
                           f"{format_number(processed)}/{format_number(total)} Dateien geprüft, {format_number(len(found))} Treffer – {format_number(seconds, 2)} s.")
                else:
                    msg = f"Fertig ({'Schnell' if mode == 'fast' else 'Vollständig'}): {format_number(len(found))} Treffer in {format_number(total)} Datei(en) – {format_number(seconds, 2)} s."
                if errors:
                    msg += f" {format_number(errors)} Datei(en) konnten nicht gelesen werden."
                self.summary_var.set(msg)
                self.status_var.set("Suche abgebrochen." if cancelled else "Suche abgeschlossen.")
                if not cancelled and not total:
                    self.status_var.set("Keine TB2-/TBL-Dateien gefunden.")
                if self.access_issues:
                    self.issues_button.configure(
                        text=f"Zugriffsprobleme ({format_number(len(self.access_issues))})")
                    self.issues_button.pack(side="left", padx=(8, 0), after=self.search_button)
            elif event[0] == "worker_error":
                if self.exit_after_scan:
                    self.destroy()
                    return
                self.progress.stop()
                self.scanning = False
                self._set_inputs_locked(False)
                self._update_search_button()
                self.status_var.set("Suche fehlgeschlagen.")
                self.summary_var.set("Keine Ergebnisse – Suche fehlgeschlagen.")
                messagebox.showerror("Suche fehlgeschlagen", event[1])
    except queue.Empty:
        pass
    self.after(100, self._poll_events)

def _fit_path_column(self, paths=None):
    """Spaltenbreite an den längsten sichtbaren Dateipfad anpassen."""
    if paths is None:
        paths = self.result_paths
    style = ttk.Style(self)
    font_name = style.lookup("Treeview", "font") or "TkDefaultFont"
    font = tkfont.nametofont(font_name) if font_name in tkfont.names(self) else tkfont.nametofont("TkDefaultFont")
    heading_width = font.measure("Dateipfad") + 32
    content_width = max((font.measure(path) for path in paths), default=0) + 24
    # Feste Spaltenbreite: manuelle Änderungen bleiben erhalten;
    # lange Pfade können horizontal gescrollt werden.
    self.tree.column("path", width=max(heading_width, content_width, 80))

def _update_open_button_state(self, _event=None):
    """Enable 'Datei öffnen' only when one result is selected."""
    selected = self.tree.selection()
    state = "normal" if len(selected) == 1 else "disabled"
    self.open_button.configure(state=state)

def open_selected_file(self):
    """Open the selected result using the Windows file association."""
    selected = self.tree.selection()
    if len(selected) != 1:
        messagebox.showinfo(
            "Datei auswählen",
            "Bitte zuerst eine Datei in der Trefferliste markieren.",
        )
        return

    values = self.tree.item(selected[0], "values")
    if values:
        self._open_file_path(str(values[0]))

def open_result_file(self, event):
    """Open the double-clicked result using Windows file associations."""
    row_id = self.tree.identify_row(event.y)
    if not row_id:
        return

    values = self.tree.item(row_id, "values")
    if values:
        self._open_file_path(str(values[0]))

def _open_file_path(self, file_path: str):
    """Open a TB2 file through the normal Windows file association."""
    if not Path(file_path).is_file():
        messagebox.showerror(
            "Datei nicht gefunden",
            f"Die gefundene Datei ist nicht mehr vorhanden oder nicht erreichbar:\n\n{file_path}",
        )
        return

    try:
        if not hasattr(os, "startfile"):
            messagebox.showerror(
                "Nur unter Windows verfügbar",
                "Das Öffnen über die Dateizuordnung ist nur unter Windows verfügbar.",
            )
            return
        # os.startfile nutzt die Windows-Dateizuordnung, genau wie ein Doppelklick
        # auf die Datei im Explorer.
        os.startfile(file_path)
        self.status_var.set(f"Datei geöffnet: {file_path}")
    except OSError as exc:
        messagebox.showerror(
            "Datei konnte nicht geöffnet werden",
            "Windows konnte für diese TB2-Datei keine passende Anwendung starten. "
            "Prüfe bitte die Dateizuordnung.\n\n"
            f"Datei: {file_path}\n\nFehler: {exc}",
        )

def copy_paths(self):
    if not self.result_paths:
        return
    self.clipboard_clear()
    self.clipboard_append("\n".join(self.result_paths))
    self.status_var.set(f"{format_number(len(self.result_paths))} Pfad/Pfade in die Zwischenablage kopiert.")

def save_paths(self):
    if not self.result_paths:
        return
    destination = filedialog.asksaveasfilename(
        title="Trefferpfade speichern",
        defaultextension=".txt",
        filetypes=[("Textdatei", "*.txt"), ("Alle Dateien", "*.*")],
        initialfile="TB2_Treffer.txt",
        initialdir=load_export_folder() or None,
    )
    if not destination:
        return
    try:
        Path(destination).write_text("\n".join(self.result_paths) + "\n", encoding="utf-8")
    except OSError as exc:
        messagebox.showerror("Speichern fehlgeschlagen", str(exc))
        return
    remember_export_folder(Path(destination).resolve().parent)
    self.status_var.set(f"Pfadliste gespeichert: {destination}")

def clear_results(self):
    if self.scanning:
        return
    self.result_paths = []
    self.access_issues = []
    self.issues_button.pack_forget()
    self.clear_button.configure(state="disabled")
    for item in self.tree.get_children():
        self.tree.delete(item)
    self.copy_button.configure(state="disabled")
    self.open_button.configure(state="disabled")
    self.save_button.configure(state="disabled")
    self._fit_path_column([])
    self.status_var.set("Ergebnisliste geleert.")
    self.summary_var.set("Noch keine Suche abgeschlossen.")

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

def show_access_issues(self):
    if not self.access_issues:
        return
    dialog = tk.Toplevel(self)
    dialog.title("Zugriffsprobleme – TB2-Textfinder")
    center_window(dialog, 780, 500, parent=self)
    dialog.minsize(480, 300)
    dialog.transient(self)
    body = ttk.Frame(dialog, padding=14)
    body.pack(fill="both", expand=True)
    ttk.Label(body, text=f"{format_number(len(self.access_issues))} übersprungene Verzeichnisse",
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

def choose_folder(self):
    folder = filedialog.askdirectory(title="Ordner mit TB2-/TBL-Dateien auswählen", initialdir=self.folder_var.get() or None)
    if folder:
        self.folder_var.set(folder)
        remember_folder(folder)

def _update_search_button(self, *_args):
    """Suche nur mit eingetragenem Ordner starten; Abbruchmodus bewahren."""
    if not self.scanning:
        self.search_button.configure(
            state="normal" if self.folder_var.get().strip() and self.term_var.get().strip() else "disabled",
            text="Suchen")

def request_exit(self):
    """Während einer Prüfung Rückfrage stellen und kontrolliert beenden."""
    if not self.scanning:
        self.destroy()
        return
    if self.exit_after_scan:
        return
    if not messagebox.askyesno(
            "Programm beenden",
            "Sind Sie sicher, dass Sie die Suche abbrechen und das Programm beenden möchten?",
            parent=self):
        return
    self.exit_after_scan = True
    self.cancel_scan_event.set()
    self.search_button.configure(state="disabled", text="Abbruch läuft …")
    self.status_var.set("Programm wird nach Abbruch der laufenden Arbeit beendet …")

def search_or_cancel(self):
    """Start a scan, or request cooperative cancellation."""
    if self.scanning:
        if not self.cancel_scan_event.is_set():
            self.cancel_scan_event.set()
            self.search_button.configure(state="disabled", text="Abbruch läuft …")
            self.status_var.set("Abbruch angefordert – laufender Verzeichniszugriff bzw. aktuelle Datei wird abgeschlossen …")
        return
    self.start_scan()

def _set_inputs_locked(self, locked):
    for widget in (self.term_entry, self.folder_entry, self.folder_button, self.recursive_check, self.whole_check, self.case_check, self.fast_radio, self.full_radio):
        widget.configure(state="disabled" if locked else "normal")

def start_scan(self):
    folder_text = self.folder_var.get().strip()
    term = self.term_var.get().strip()
    if not folder_text or not Path(folder_text).is_dir():
        messagebox.showwarning("Ordner fehlt", "Bitte einen gültigen Ordner auswählen.")
        return
    if not term:
        messagebox.showwarning("Suchtext fehlt", "Bitte einen Suchtext eingeben.")
        return
    if self.scanning:
        return
    remember_folder(folder_text)
    self.cancel_scan_event.clear()
    self.scanning = True
    self._set_inputs_locked(True)
    self.result_paths = []
    self.access_issues = []
    self.issues_button.pack_forget()
    self.search_button.configure(state="normal", text="Suche abbrechen")
    self.clear_button.configure(state="disabled")
    self.copy_button.configure(state="disabled")
    self.open_button.configure(state="disabled")
    self.save_button.configure(state="disabled")
    for item in self.tree.get_children():
        self.tree.delete(item)
    self._fit_path_column([])
    self.progress.configure(mode="indeterminate", value=0)
    self.progress.start(12)
    self.summary_var.set("Suche läuft – Ergebnis folgt nach Abschluss oder Abbruch.")
    self.status_var.set("Durchsuche Verzeichnisstruktur nach TB2-/TBL-Dateien …")
    threading.Thread(
        target=self._discover_and_scan,
        args=(Path(folder_text), self.recursive_var.get(), term,
              self.case_var.get(), self.search_mode_var.get(), self.whole_word_var.get()),
        daemon=True,
    ).start()

def _discover_and_scan(self, root: Path, recursive: bool, term: str,
                       case_sensitive: bool, mode: str, whole_word: bool):
    files = []
    skipped = []
    directories_checked = 0

    def on_walk_error(exc):
        skipped.append(f"{exc.filename or 'Unbekannter Ordner'}: {exc}")

    try:
        if recursive:
            directories = os.walk(root, topdown=True, followlinks=False,
                                  onerror=on_walk_error)
        else:
            def one_directory():
                try:
                    with os.scandir(root) as entries:
                        yield str(root), [], [entry.name for entry in entries
                                               if entry.is_file(follow_symlinks=False)]
                except OSError as exc:
                    on_walk_error(exc)
            directories = one_directory()

        for directory, subdirs, names in directories:
            if self.cancel_scan_event.is_set():
                break
            directories_checked += 1
            if recursive:
                subdirs[:] = [name for name in subdirs
                              if not getattr(os.path, "isjunction", lambda p: False)(os.path.join(directory, name))]
            for name in names:
                if name.lower().endswith((".tb2", ".tbl")):
                    files.append(Path(directory) / name)
            if directories_checked % 50 == 0:
                self.events.put(("discovery", directories_checked, len(files)))
        self.events.put(("discovery_done", len(files), directories_checked, skipped))
        if self.cancel_scan_event.is_set() or not files:
            self.events.put(("finished", [], len(files), 0, mode, 0.0, 0,
                             self.cancel_scan_event.is_set()))
            return
        self._scan_worker(files, term, case_sensitive, mode, whole_word)
    except Exception as exc:
        self.events.put(("worker_error", str(exc)))

def _scan_worker(self, files: list[Path], term: str, case_sensitive: bool, mode: str, whole_word: bool):
    found: list[str] = []
    errors = 0
    started = perf_counter()
    processed = 0
    for index, path in enumerate(files, start=1):
        if self.cancel_scan_event.is_set():
            break
        if mode == "fast":
            try:
                from tb2.jpeg_fast import contains_term_fast
                data = mask_resource_paths(path.read_bytes())
                # Zweistufige Ganzwortsuche: Nur Kandidaten mit einem
                # Teilworttreffer benötigen die teure Wortgrenzenprüfung.
                # JPEG-Bereiche werden in beiden Stufen identisch behandelt.
                candidate = contains_term_fast(data, term, case_sensitive)
                if whole_word and candidate:
                    from tb2.jpeg_fast import jpeg_ranges
                    spans = jpeg_ranges(data)
                    previous = 0
                    hit = False
                    for begin, end in spans:
                        if begin > previous and contains_whole_word(data[previous:begin], term, case_sensitive):
                            hit = True
                            break
                        previous = max(previous, end)
                    if not hit and previous < len(data):
                        hit = contains_whole_word(data[previous:], term, case_sensitive)
                else:
                    hit = candidate
                error = None
            except (OSError, ValueError, MemoryError) as exc:
                hit, error = False, str(exc)
        else:
            hit, error = scan_file(path, term, case_sensitive, whole_word)
        if hit:
            found.append(str(path.resolve()))
        if error:
            errors += 1
        processed = index
        self.events.put(("progress", index, len(files), path.name))
    self.events.put(("finished", found, len(files), errors, mode, perf_counter() - started,
                     processed, self.cancel_scan_event.is_set()))

def _poll_events(self):
    try:
        while True:
            event = self.events.get_nowait()
            if event[0] == "discovery":
                _, directories, found = event
                if not self.cancel_scan_event.is_set():
                    self.status_var.set(
                        f"Durchsuche Verzeichnisse: {format_number(directories)} Ordner, "
                        f"{format_number(found)} TB2-/TBL-Datei(en) gefunden …")
            elif event[0] == "discovery_done":
                _, total, directories, skipped = event
                self.access_issues = skipped
                self.progress.stop()
                self.progress.configure(mode="determinate", maximum=max(total, 1), value=0)
                if not self.cancel_scan_event.is_set():
                    self.status_var.set(
                        f"Dateisuche abgeschlossen: {format_number(directories)} Ordner, "
                        f"{format_number(total)} TB2-/TBL-Datei(en). Suche läuft …")
            elif event[0] == "progress":
                _, current, total, filename = event
                self.progress.configure(value=current)
                if not self.cancel_scan_event.is_set():
                    self.status_var.set(f"Datei {format_number(current)}/{format_number(total)}: {filename}")
            elif event[0] == "finished":
                if self.exit_after_scan:
                    self.destroy()
                    return
                _, found, total, errors, mode, seconds, processed, cancelled = event
                self.progress.stop()
                self.result_paths = found
                for index, path in enumerate(found):
                    self.tree.insert("", "end", values=(path,), tags=row_tags(index))
                self._fit_path_column(found)
                self.scanning = False
                self._set_inputs_locked(False)
                self._update_search_button()
                self.clear_button.configure(state="normal" if found else "disabled")
                state = "normal" if found else "disabled"
                self.copy_button.configure(state=state)
                self.save_button.configure(state=state)
                # Die Datei-Öffnen-Schaltfläche wird erst nach Auswahl eines Treffers aktiviert.
                self.open_button.configure(state="disabled")
                if cancelled:
                    msg = (f"Abgebrochen ({'Schnell' if mode == 'fast' else 'Vollständig'}): "
                           f"{format_number(processed)}/{format_number(total)} Dateien geprüft, {format_number(len(found))} Treffer – {format_number(seconds, 2)} s.")
                else:
                    msg = f"Fertig ({'Schnell' if mode == 'fast' else 'Vollständig'}): {format_number(len(found))} Treffer in {format_number(total)} Datei(en) – {format_number(seconds, 2)} s."
                if errors:
                    msg += f" {format_number(errors)} Datei(en) konnten nicht gelesen werden."
                self.summary_var.set(msg)
                self.status_var.set("Suche abgebrochen." if cancelled else "Suche abgeschlossen.")
                if not cancelled and not total:
                    self.status_var.set("Keine TB2-/TBL-Dateien gefunden.")
                if self.access_issues:
                    self.issues_button.configure(
                        text=f"Zugriffsprobleme ({format_number(len(self.access_issues))})")
                    self.issues_button.pack(side="left", padx=(8, 0), after=self.search_button)
            elif event[0] == "worker_error":
                if self.exit_after_scan:
                    self.destroy()
                    return
                self.progress.stop()
                self.scanning = False
                self._set_inputs_locked(False)
                self._update_search_button()
                self.status_var.set("Suche fehlgeschlagen.")
                self.summary_var.set("Keine Ergebnisse – Suche fehlgeschlagen.")
                messagebox.showerror("Suche fehlgeschlagen", event[1])
    except queue.Empty:
        pass
    self.after(100, self._poll_events)

def _fit_path_column(self, paths=None):
    """Spaltenbreite an den längsten sichtbaren Dateipfad anpassen."""
    if paths is None:
        paths = self.result_paths
    style = ttk.Style(self)
    font_name = style.lookup("Treeview", "font") or "TkDefaultFont"
    font = tkfont.nametofont(font_name) if font_name in tkfont.names(self) else tkfont.nametofont("TkDefaultFont")
    heading_width = font.measure("Dateipfad") + 32
    content_width = max((font.measure(path) for path in paths), default=0) + 24
    # Feste Spaltenbreite: manuelle Änderungen bleiben erhalten;
    # lange Pfade können horizontal gescrollt werden.
    self.tree.column("path", width=max(heading_width, content_width, 80))

def _update_open_button_state(self, _event=None):
    """Enable 'Datei öffnen' only when one result is selected."""
    selected = self.tree.selection()
    state = "normal" if len(selected) == 1 else "disabled"
    self.open_button.configure(state=state)

def open_selected_file(self):
    """Open the selected result using the Windows file association."""
    selected = self.tree.selection()
    if len(selected) != 1:
        messagebox.showinfo(
            "Datei auswählen",
            "Bitte zuerst eine Datei in der Trefferliste markieren.",
        )
        return

    values = self.tree.item(selected[0], "values")
    if values:
        self._open_file_path(str(values[0]))

def open_result_file(self, event):
    """Open the double-clicked result using Windows file associations."""
    row_id = self.tree.identify_row(event.y)
    if not row_id:
        return

    values = self.tree.item(row_id, "values")
    if values:
        self._open_file_path(str(values[0]))

def _open_file_path(self, file_path: str):
    """Open a TB2 file through the normal Windows file association."""
    if not Path(file_path).is_file():
        messagebox.showerror(
            "Datei nicht gefunden",
            f"Die gefundene Datei ist nicht mehr vorhanden oder nicht erreichbar:\n\n{file_path}",
        )
        return

    try:
        if not hasattr(os, "startfile"):
            messagebox.showerror(
                "Nur unter Windows verfügbar",
                "Das Öffnen über die Dateizuordnung ist nur unter Windows verfügbar.",
            )
            return
        # os.startfile nutzt die Windows-Dateizuordnung, genau wie ein Doppelklick
        # auf die Datei im Explorer.
        os.startfile(file_path)
        self.status_var.set(f"Datei geöffnet: {file_path}")
    except OSError as exc:
        messagebox.showerror(
            "Datei konnte nicht geöffnet werden",
            "Windows konnte für diese TB2-Datei keine passende Anwendung starten. "
            "Prüfe bitte die Dateizuordnung.\n\n"
            f"Datei: {file_path}\n\nFehler: {exc}",
        )

def copy_paths(self):
    if not self.result_paths:
        return
    self.clipboard_clear()
    self.clipboard_append("\n".join(self.result_paths))
    self.status_var.set(f"{format_number(len(self.result_paths))} Pfad/Pfade in die Zwischenablage kopiert.")

def save_paths(self):
    if not self.result_paths:
        return
    destination = filedialog.asksaveasfilename(
        title="Trefferpfade speichern",
        defaultextension=".txt",
        filetypes=[("Textdatei", "*.txt"), ("Alle Dateien", "*.*")],
        initialfile="TB2_Treffer.txt",
        initialdir=load_export_folder() or None,
    )
    if not destination:
        return
    try:
        Path(destination).write_text("\n".join(self.result_paths) + "\n", encoding="utf-8")
    except OSError as exc:
        messagebox.showerror("Speichern fehlgeschlagen", str(exc))
        return
    remember_export_folder(Path(destination).resolve().parent)
    self.status_var.set(f"Pfadliste gespeichert: {destination}")

def clear_results(self):
    if self.scanning:
        return
    self.result_paths = []
    self.access_issues = []
    self.issues_button.pack_forget()
    self.clear_button.configure(state="disabled")
    for item in self.tree.get_children():
        self.tree.delete(item)
    self.copy_button.configure(state="disabled")
    self.open_button.configure(state="disabled")
    self.save_button.configure(state="disabled")
    self._fit_path_column([])
    self.status_var.set("Ergebnisliste geleert.")
    self.summary_var.set("Noch keine Suche abgeschlossen.")

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

def choose_folder(parent):
    folder = filedialog.askdirectory(title="Ordner mit TB2-/TBL-Dateien auswählen", initialdir=parent.folder_var.get() or None)
    if folder:
        parent.folder_var.set(folder)
        remember_folder(folder)

def _update_search_button(parent, *_args):
    """Suche nur mit eingetragenem Ordner starten; Abbruchmodus bewahren."""
    if not parent.scanning:
        parent.search_button.configure(
            state="normal" if parent.folder_var.get().strip() and parent.term_var.get().strip() else "disabled",
            text="Suchen")

def request_exit(parent):
    """Während einer Prüfung Rückfrage stellen und kontrolliert beenden."""
    if not parent.scanning:
        parent.destroy()
        return
    if parent.exit_after_scan:
        return
    if not messagebox.askyesno(
            "Programm beenden",
            "Sind Sie sicher, dass Sie die Suche abbrechen und das Programm beenden möchten?",
            parent=parent):
        return
    parent.exit_after_scan = True
    parent.cancel_scan_event.set()
    parent.search_button.configure(state="disabled", text="Abbruch läuft …")
    parent.status_var.set("Programm wird nach Abbruch der laufenden Arbeit beendet …")

def search_or_cancel(parent):
    """Start a scan, or request cooperative cancellation."""
    if parent.scanning:
        if not parent.cancel_scan_event.is_set():
            parent.cancel_scan_event.set()
            parent.search_button.configure(state="disabled", text="Abbruch läuft …")
            parent.status_var.set("Abbruch angefordert – laufender Verzeichniszugriff bzw. aktuelle Datei wird abgeschlossen …")
        return
    parent.start_scan()

def _set_inputs_locked(parent, locked):
    for widget in (parent.term_entry, parent.folder_entry, parent.folder_button, parent.recursive_check, parent.whole_check, parent.case_check, parent.fast_radio, parent.full_radio):
        widget.configure(state="disabled" if locked else "normal")

def start_scan(parent):
    folder_text = parent.folder_var.get().strip()
    term = parent.term_var.get().strip()
    if not folder_text or not Path(folder_text).is_dir():
        messagebox.showwarning("Ordner fehlt", "Bitte einen gültigen Ordner auswählen.")
        return
    if not term:
        messagebox.showwarning("Suchtext fehlt", "Bitte einen Suchtext eingeben.")
        return
    if parent.scanning:
        return
    remember_folder(folder_text)
    parent.cancel_scan_event.clear()
    parent.scanning = True
    parent._set_inputs_locked(True)
    parent.result_paths = []
    issues = []
    parent.issues_button.pack_forget()
    parent.search_button.configure(state="normal", text="Suche abbrechen")
    parent.clear_button.configure(state="disabled")
    parent.copy_button.configure(state="disabled")
    parent.open_button.configure(state="disabled")
    parent.save_button.configure(state="disabled")
    for item in parent.tree.get_children():
        parent.tree.delete(item)
    parent._fit_path_column([])
    parent.progress.configure(mode="indeterminate", value=0)
    parent.progress.start(12)
    parent.summary_var.set("Suche läuft – Ergebnis folgt nach Abschluss oder Abbruch.")
    parent.status_var.set("Durchsuche Verzeichnisstruktur nach TB2-/TBL-Dateien …")
    threading.Thread(
        target=parent._discover_and_scan,
        args=(Path(folder_text), parent.recursive_var.get(), term,
              parent.case_var.get(), parent.search_mode_var.get(), parent.whole_word_var.get()),
        daemon=True,
    ).start()

def _discover_and_scan(parent, root: Path, recursive: bool, term: str,
                       case_sensitive: bool, mode: str, whole_word: bool):
    files = []
    skipped = []
    directories_checked = 0

    def on_walk_error(exc):
        skipped.append(f"{exc.filename or 'Unbekannter Ordner'}: {exc}")

    try:
        if recursive:
            directories = os.walk(root, topdown=True, followlinks=False,
                                  onerror=on_walk_error)
        else:
            def one_directory():
                try:
                    with os.scandir(root) as entries:
                        yield str(root), [], [entry.name for entry in entries
                                               if entry.is_file(follow_symlinks=False)]
                except OSError as exc:
                    on_walk_error(exc)
            directories = one_directory()

        for directory, subdirs, names in directories:
            if parent.cancel_scan_event.is_set():
                break
            directories_checked += 1
            if recursive:
                subdirs[:] = [name for name in subdirs
                              if not getattr(os.path, "isjunction", lambda p: False)(os.path.join(directory, name))]
            for name in names:
                if name.lower().endswith((".tb2", ".tbl")):
                    files.append(Path(directory) / name)
            if directories_checked % 50 == 0:
                parent.events.put(("discovery", directories_checked, len(files)))
        parent.events.put(("discovery_done", len(files), directories_checked, skipped))
        if parent.cancel_scan_event.is_set() or not files:
            parent.events.put(("finished", [], len(files), 0, mode, 0.0, 0,
                             parent.cancel_scan_event.is_set()))
            return
        parent._scan_worker(files, term, case_sensitive, mode, whole_word)
    except Exception as exc:
        parent.events.put(("worker_error", str(exc)))

def _scan_worker(parent, files: list[Path], term: str, case_sensitive: bool, mode: str, whole_word: bool):
    found: list[str] = []
    errors = 0
    started = perf_counter()
    processed = 0
    for index, path in enumerate(files, start=1):
        if parent.cancel_scan_event.is_set():
            break
        if mode == "fast":
            try:
                from tb2.jpeg_fast import contains_term_fast
                data = mask_resource_paths(path.read_bytes())
                # Zweistufige Ganzwortsuche: Nur Kandidaten mit einem
                # Teilworttreffer benötigen die teure Wortgrenzenprüfung.
                # JPEG-Bereiche werden in beiden Stufen identisch behandelt.
                candidate = contains_term_fast(data, term, case_sensitive)
                if whole_word and candidate:
                    from tb2.jpeg_fast import jpeg_ranges
                    spans = jpeg_ranges(data)
                    previous = 0
                    hit = False
                    for begin, end in spans:
                        if begin > previous and contains_whole_word(data[previous:begin], term, case_sensitive):
                            hit = True
                            break
                        previous = max(previous, end)
                    if not hit and previous < len(data):
                        hit = contains_whole_word(data[previous:], term, case_sensitive)
                else:
                    hit = candidate
                error = None
            except (OSError, ValueError, MemoryError) as exc:
                hit, error = False, str(exc)
        else:
            hit, error = scan_file(path, term, case_sensitive, whole_word)
        if hit:
            found.append(str(path.resolve()))
        if error:
            errors += 1
        processed = index
        parent.events.put(("progress", index, len(files), path.name))
    parent.events.put(("finished", found, len(files), errors, mode, perf_counter() - started,
                     processed, parent.cancel_scan_event.is_set()))

def _poll_events(parent):
    try:
        while True:
            event = parent.events.get_nowait()
            if event[0] == "discovery":
                _, directories, found = event
                if not parent.cancel_scan_event.is_set():
                    parent.status_var.set(
                        f"Durchsuche Verzeichnisse: {format_number(directories)} Ordner, "
                        f"{format_number(found)} TB2-/TBL-Datei(en) gefunden …")
            elif event[0] == "discovery_done":
                _, total, directories, skipped = event
                issues = skipped
                parent.progress.stop()
                parent.progress.configure(mode="determinate", maximum=max(total, 1), value=0)
                if not parent.cancel_scan_event.is_set():
                    parent.status_var.set(
                        f"Dateisuche abgeschlossen: {format_number(directories)} Ordner, "
                        f"{format_number(total)} TB2-/TBL-Datei(en). Suche läuft …")
            elif event[0] == "progress":
                _, current, total, filename = event
                parent.progress.configure(value=current)
                if not parent.cancel_scan_event.is_set():
                    parent.status_var.set(f"Datei {format_number(current)}/{format_number(total)}: {filename}")
            elif event[0] == "finished":
                if parent.exit_after_scan:
                    parent.destroy()
                    return
                _, found, total, errors, mode, seconds, processed, cancelled = event
                parent.progress.stop()
                parent.result_paths = found
                for index, path in enumerate(found):
                    parent.tree.insert("", "end", values=(path,), tags=row_tags(index))
                parent._fit_path_column(found)
                parent.scanning = False
                parent._set_inputs_locked(False)
                parent._update_search_button()
                parent.clear_button.configure(state="normal" if found else "disabled")
                state = "normal" if found else "disabled"
                parent.copy_button.configure(state=state)
                parent.save_button.configure(state=state)
                # Die Datei-Öffnen-Schaltfläche wird erst nach Auswahl eines Treffers aktiviert.
                parent.open_button.configure(state="disabled")
                if cancelled:
                    msg = (f"Abgebrochen ({'Schnell' if mode == 'fast' else 'Vollständig'}): "
                           f"{format_number(processed)}/{format_number(total)} Dateien geprüft, {format_number(len(found))} Treffer – {format_number(seconds, 2)} s.")
                else:
                    msg = f"Fertig ({'Schnell' if mode == 'fast' else 'Vollständig'}): {format_number(len(found))} Treffer in {format_number(total)} Datei(en) – {format_number(seconds, 2)} s."
                if errors:
                    msg += f" {format_number(errors)} Datei(en) konnten nicht gelesen werden."
                parent.summary_var.set(msg)
                parent.status_var.set("Suche abgebrochen." if cancelled else "Suche abgeschlossen.")
                if not cancelled and not total:
                    parent.status_var.set("Keine TB2-/TBL-Dateien gefunden.")
                if issues:
                    parent.issues_button.configure(
                        text=f"Zugriffsprobleme ({format_number(len(issues))})")
                    parent.issues_button.pack(side="left", padx=(8, 0), after=parent.search_button)
            elif event[0] == "worker_error":
                if parent.exit_after_scan:
                    parent.destroy()
                    return
                parent.progress.stop()
                parent.scanning = False
                parent._set_inputs_locked(False)
                parent._update_search_button()
                parent.status_var.set("Suche fehlgeschlagen.")
                parent.summary_var.set("Keine Ergebnisse – Suche fehlgeschlagen.")
                messagebox.showerror("Suche fehlgeschlagen", event[1])
    except queue.Empty:
        pass
    parent.after(100, parent._poll_events)

def _fit_path_column(parent, paths=None):
    """Spaltenbreite an den längsten sichtbaren Dateipfad anpassen."""
    if paths is None:
        paths = parent.result_paths
    style = ttk.Style(parent)
    font_name = style.lookup("Treeview", "font") or "TkDefaultFont"
    font = tkfont.nametofont(font_name) if font_name in tkfont.names(parent) else tkfont.nametofont("TkDefaultFont")
    heading_width = font.measure("Dateipfad") + 32
    content_width = max((font.measure(path) for path in paths), default=0) + 24
    # Feste Spaltenbreite: manuelle Änderungen bleiben erhalten;
    # lange Pfade können horizontal gescrollt werden.
    parent.tree.column("path", width=max(heading_width, content_width, 80))

def _update_open_button_state(parent, _event=None):
    """Enable 'Datei öffnen' only when one result is selected."""
    selected = parent.tree.selection()
    state = "normal" if len(selected) == 1 else "disabled"
    parent.open_button.configure(state=state)

def open_selected_file(parent):
    """Open the selected result using the Windows file association."""
    selected = parent.tree.selection()
    if len(selected) != 1:
        messagebox.showinfo(
            "Datei auswählen",
            "Bitte zuerst eine Datei in der Trefferliste markieren.",
        )
        return

    values = parent.tree.item(selected[0], "values")
    if values:
        parent._open_file_path(str(values[0]))

def open_result_file(parent, event):
    """Open the double-clicked result using Windows file associations."""
    row_id = parent.tree.identify_row(event.y)
    if not row_id:
        return

    values = parent.tree.item(row_id, "values")
    if values:
        parent._open_file_path(str(values[0]))

def _open_file_path(parent, file_path: str):
    """Open a TB2 file through the normal Windows file association."""
    if not Path(file_path).is_file():
        messagebox.showerror(
            "Datei nicht gefunden",
            f"Die gefundene Datei ist nicht mehr vorhanden oder nicht erreichbar:\n\n{file_path}",
        )
        return

    try:
        if not hasattr(os, "startfile"):
            messagebox.showerror(
                "Nur unter Windows verfügbar",
                "Das Öffnen über die Dateizuordnung ist nur unter Windows verfügbar.",
            )
            return
        # os.startfile nutzt die Windows-Dateizuordnung, genau wie ein Doppelklick
        # auf die Datei im Explorer.
        os.startfile(file_path)
        parent.status_var.set(f"Datei geöffnet: {file_path}")
    except OSError as exc:
        messagebox.showerror(
            "Datei konnte nicht geöffnet werden",
            "Windows konnte für diese TB2-Datei keine passende Anwendung starten. "
            "Prüfe bitte die Dateizuordnung.\n\n"
            f"Datei: {file_path}\n\nFehler: {exc}",
        )

def copy_paths(parent):
    if not parent.result_paths:
        return
    parent.clipboard_clear()
    parent.clipboard_append("\n".join(parent.result_paths))
    parent.status_var.set(f"{format_number(len(parent.result_paths))} Pfad/Pfade in die Zwischenablage kopiert.")

def save_paths(parent):
    if not parent.result_paths:
        return
    destination = filedialog.asksaveasfilename(
        title="Trefferpfade speichern",
        defaultextension=".txt",
        filetypes=[("Textdatei", "*.txt"), ("Alle Dateien", "*.*")],
        initialfile="TB2_Treffer.txt",
        initialdir=load_export_folder() or None,
    )
    if not destination:
        return
    try:
        Path(destination).write_text("\n".join(parent.result_paths) + "\n", encoding="utf-8")
    except OSError as exc:
        messagebox.showerror("Speichern fehlgeschlagen", str(exc))
        return
    remember_export_folder(Path(destination).resolve().parent)
    parent.status_var.set(f"Pfadliste gespeichert: {destination}")

def clear_results(parent):
    if parent.scanning:
        return
    parent.result_paths = []
    issues = []
    parent.issues_button.pack_forget()
    parent.clear_button.configure(state="disabled")
    for item in parent.tree.get_children():
        parent.tree.delete(item)
    parent.copy_button.configure(state="disabled")
    parent.open_button.configure(state="disabled")
    parent.save_button.configure(state="disabled")
    parent._fit_path_column([])
    parent.status_var.set("Ergebnisliste geleert.")
    parent.summary_var.set("Noch keine Suche abgeschlossen.")

