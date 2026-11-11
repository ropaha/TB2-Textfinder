#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TB2-Negativtester: prüft Dateien auf bislang bekannte TB2-Textmuster."""
from __future__ import annotations

import os
import queue
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from TB2_Textfinder import has_variable_80_pattern, has_wide_587_pattern, has_early_80_pattern, has_early_82_pattern, has_variable_98_pattern, has_variable_106_pattern

APP_VERSION = "1.8.5"
MIN_CHARACTERS = 3

# Empirisch beobachtete Marker und Abstände aus dem TB2-Textfinder-Projekt.
PROFILES = (
    ("SignumNext-Profil A", b"\x81\x00\x00", (0x6A,)),
    ("SignumNext-Profil B", b"\x81\x67\x66\x66\x66\x66\x81", (0x6A,)),
    ("Signum-Altformat", b"\x81\x00\x00", (0x50,)),
    ("Signum-Frühformat", b"\x81\x7C\xE9\xE4\x58\x09", (0x50,)),
    ("Signum-90er-Profil", b"\x81\x00\x00", (0x62,)),
)


def _find_all(data: bytes, needle: bytes):
    start = 0
    while True:
        pos = data.find(needle, start)
        if pos < 0:
            return
        yield pos
        start = pos + 1


def _printable_codes() -> set[int]:
    result: set[int] = set()
    for encoding in ("cp850", "cp437", "cp1252", "latin-1"):
        for value in range(256):
            try:
                char = bytes([value]).decode(encoding)
            except UnicodeDecodeError:
                continue
            if char.isprintable() or char.isspace():
                result.add(value)
    return result


PRINTABLE_CODES = _printable_codes()


def has_known_glyph_pattern(data: bytes, minimum: int = MIN_CHARACTERS) -> bool:
    """Mindestens N Zeichen müssen im bekannten Markerabstand aufeinanderfolgen."""
    if not data or minimum < 1:
        return False
    for _name, marker, strides in PROFILES:
        marker_length = len(marker)
        for stride in strides:
            offsets = (1, 7) if stride == 0x50 and marker == b"\x81\x00\x00" else ((7,) if stride == 0x62 else (1,))
            for marker_offset in offsets:
                for marker_pos in _find_all(data, marker):
                    first_char_pos = marker_pos - marker_offset
                    if first_char_pos < 0 or data[first_char_pos] not in PRINTABLE_CODES:
                        continue
                    matched = True
                    for index in range(1, minimum):
                        char_pos = first_char_pos + index * stride
                        next_marker_pos = char_pos + marker_offset
                        if (char_pos >= len(data)
                                or data[char_pos] not in PRINTABLE_CODES
                                or data[next_marker_pos:next_marker_pos + marker_length] != marker):
                            matched = False
                            break
                    if matched:
                        return True
    return (has_variable_80_pattern(data, minimum)
            or has_wide_587_pattern(data, minimum)
            or has_early_80_pattern(data, minimum)
            or has_early_82_pattern(data, minimum)
            or has_variable_98_pattern(data, minimum)
            or has_variable_106_pattern(data, minimum))


def inspect_file(path: Path) -> tuple[str, str]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        return "Fehler", str(exc)
    if not data:
        return "Leer", "Datei enthält 0 Bytes"
    if has_known_glyph_pattern(data):
        return "Erkannt", "Bekanntes Muster (mindestens 3 Zeichen)"
    if has_known_glyph_pattern(data, minimum=2):
        return "Fragment", "Könnte Text enthalten, muss analysiert werden"
    return "Vermutlich kein Text", "Enthält vermutlich keinen Text"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"TB2-Negativtester – {APP_VERSION}")
        self.geometry("1000x650")
        self.minsize(760, 460)
        self.events: queue.Queue = queue.Queue()
        self.scanning = False
        self.rows: list[tuple[str, str, str]] = []
        self.ignored_paths: set[str] = set()
        self.filter_var = tk.StringVar(value="Alle auffälligen Dateien")
        self.filter_options = {
            "Alle auffälligen Dateien": None,
            "Könnte Text enthalten, muss analysiert werden": {"Fragment"},
            "Enthält vermutlich keinen Text": {"Vermutlich kein Text"},
            "Lesefehler / Leere Dateien": {"Fehler", "Leer"},
            "Ignoriert": {"Ignoriert"},
        }
        self.scan_summary = ""
        self._build_ui()
        self.after(100, self._poll_events)

    def _build_ui(self):
        frame = ttk.Frame(self, padding=14)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Zu prüfender Ordner:").grid(row=0, column=0, sticky="w")
        self.folder_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.folder_var).grid(row=0, column=1, sticky="ew", padx=10)
        ttk.Button(frame, text="Ordner wählen …", command=self.choose_folder).grid(row=0, column=2)
        self.recursive_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame, text="Unterordner einbeziehen", variable=self.recursive_var).grid(
            row=1, column=1, sticky="w", pady=(9, 2))
        actions = ttk.Frame(frame)
        actions.grid(row=2, column=0, columnspan=3, sticky="w", pady=(12, 10))
        self.scan_button = ttk.Button(actions, text="Ordner prüfen", command=self.start_scan)
        self.scan_button.pack(side="left")
        self.open_button = ttk.Button(actions, text="Datei öffnen", command=self.open_selected, state="disabled")
        self.open_button.pack(side="left", padx=(8, 0))
        self.ignore_button = ttk.Button(actions, text="Ignorieren", command=self.toggle_ignore, state="disabled")
        self.ignore_button.pack(side="left", padx=(8, 0))
        self.copy_button = ttk.Button(actions, text="Pfade kopieren", command=self.copy_paths, state="disabled")
        self.copy_button.pack(side="left", padx=(8, 0))
        self.save_button = ttk.Button(actions, text="Liste als TXT speichern …", command=self.save_report, state="disabled")
        self.save_button.pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Leeren", command=self.clear).pack(side="left", padx=(8, 0))
        self.progress = ttk.Progressbar(frame, mode="determinate")
        self.progress.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 7))
        self.status_var = tk.StringVar(value="Bereit. Ordner auswählen und Prüfung starten.")
        ttk.Label(frame, textvariable=self.status_var).grid(row=4, column=0, columnspan=3, sticky="w", pady=(0, 8))
        filters = ttk.Frame(frame)
        filters.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(3, 7))
        ttk.Label(filters, text="Trefferliste filtern:").pack(side="left", padx=(0, 9))
        self.filter_box = ttk.Combobox(filters, textvariable=self.filter_var, state="readonly",
                                       values=list(self.filter_options), width=51)
        self.filter_box.pack(side="left")
        self.filter_box.bind("<<ComboboxSelected>>", self.apply_filter)
        self.visible_count_var = tk.StringVar(value="Noch keine Ergebnisse")
        ttk.Label(filters, textvariable=self.visible_count_var).pack(side="left", padx=(14, 0))
        self.tree = ttk.Treeview(frame, columns=("category", "path", "detail"), show="headings")
        self.tree.heading("category", text="Status")
        self.tree.heading("path", text="Vollständiger Dateipfad")
        self.tree.heading("detail", text="Hinweis")
        self.tree.column("category", width=160, stretch=False)
        self.tree.tag_configure("ignored", foreground="#777777")
        self.tree.column("path", width=600, anchor="w")
        self.tree.column("detail", width=240, anchor="w")
        self.tree.grid(row=6, column=0, columnspan=2, sticky="nsew")
        yscroll = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        yscroll.grid(row=6, column=2, sticky="ns")
        self.tree.configure(yscrollcommand=yscroll.set)
        xscroll = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
        xscroll.grid(row=7, column=0, columnspan=2, sticky="ew")
        self.tree.configure(xscrollcommand=xscroll.set)
        self.tree.bind("<Double-1>", self.open_result)
        self.tree.bind("<<TreeviewSelect>>", self.update_buttons)
        note = ("Erkannt: mindestens 3 zusammenhängende Zeichen im bekannten TB2-Muster. "
                "Fragment: 2 Zeichen in passender Struktur – könnte Text enthalten, muss analysiert werden. "
                "Ohne Treffer: enthält vermutlich keinen Text. Dies ist keine sichere Aussage; "
                "unbekannte Kodierungen können übersehen werden. Leer und Fehler werden separat gemeldet.")
        ttk.Label(frame, text=note, wraplength=950, foreground="#555555").grid(
            row=8, column=0, columnspan=3, sticky="w", pady=(10, 0))
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(6, weight=1)

    def choose_folder(self):
        folder = filedialog.askdirectory(title="Ordner mit TB2-/TBL-Dateien auswählen")
        if folder:
            self.folder_var.set(folder)

    def start_scan(self):
        folder_text = self.folder_var.get().strip()
        if not folder_text or not Path(folder_text).is_dir():
            messagebox.showwarning("Ordner fehlt", "Bitte einen gültigen Ordner auswählen.")
            return
        if self.scanning:
            return
        root = Path(folder_text).resolve()
        candidates = root.rglob("*") if self.recursive_var.get() else root.glob("*")
        files = [p for p in candidates if p.is_file() and p.suffix.lower() in {".tb2", ".tbl"}]
        try:
            ignored = set()
            for directory in {p.parent for p in files}:
                ignore_file = directory / "ignore.txt"
                if not ignore_file.is_file():
                    continue
                for line in ignore_file.read_text(encoding="utf-8").splitlines():
                    entry = line.strip()
                    if entry and not entry.startswith("#"):
                        ignored.add(self._path_key(directory / entry))
        except (OSError, UnicodeError) as exc:
            messagebox.showerror("Ignorierliste nicht lesbar", str(exc))
            return
        self.ignored_paths = ignored
        if not files:
            messagebox.showinfo("Keine TB2-/TBL-Dateien", "Im Ordner wurden keine .TB2- oder .TBL-Dateien gefunden.")
            return
        self.scanning = True
        self.rows = []
        self.scan_summary = ""
        self.apply_filter()
        self.scan_button.configure(state="disabled")
        self.copy_button.configure(state="disabled")
        self.save_button.configure(state="disabled")
        self.open_button.configure(state="disabled")
        self.ignore_button.configure(state="disabled")
        self.progress.configure(maximum=len(files), value=0)
        self.status_var.set(f"Prüfe {len(files)} TB2-/TBL-Datei(en) …")
        threading.Thread(target=self._worker, args=(files,), daemon=True).start()

    def _worker(self, files: list[Path]):
        flagged = []
        recognized = errors = empty = fragments = probably_no_text = 0
        for index, path in enumerate(files, start=1):
            category, detail = inspect_file(path)
            if category == "Erkannt":
                recognized += 1
            else:
                flagged.append((category, str(path.resolve()), detail))
                if category == "Fehler":
                    errors += 1
                elif category == "Leer":
                    empty += 1
                elif category == "Fragment":
                    fragments += 1
                elif category == "Vermutlich kein Text":
                    probably_no_text += 1
            self.events.put(("progress", index, len(files), path.name))
        self.events.put(("finished", flagged, len(files), recognized, fragments, probably_no_text, empty, errors))

    def _poll_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                if event[0] == "progress":
                    _, current, total, name = event
                    self.progress.configure(value=current)
                    self.status_var.set(f"Datei {current}/{total}: {name}")
                elif event[0] == "finished":
                    _, flagged, total, recognized, fragments, probably_no_text, empty, errors = event
                    self.rows = flagged
                    self.apply_filter()
                    self.scanning = False
                    self.scan_button.configure(state="normal")
                    self.scan_summary = (
                        f"Fertig: {total} Datei(en) geprüft | {recognized} erkannt | "
                        f"{fragments} Fragmente | {probably_no_text} vermutlich ohne Text | "
                        f"{empty} leer | {errors} Lesefehler.")
                    self.status_var.set(self.scan_summary)
        except queue.Empty:
            pass
        self.after(100, self._poll_events)

    @staticmethod
    def _path_key(path: Path) -> str:
        return os.path.normcase(os.path.abspath(path))

    def is_ignored(self, path: str) -> bool:
        return self._path_key(Path(path)) in self.ignored_paths

    def filtered_rows(self):
        selected_filter = self.filter_var.get()
        if selected_filter == "Ignoriert":
            return [row for row in self.rows if self.is_ignored(row[1])]
        allowed = self.filter_options.get(selected_filter)
        return [row for row in self.rows if allowed is None or
                (not self.is_ignored(row[1]) and row[0] in allowed)]

    def apply_filter(self, _event=None):
        selected_path = self.selected_path() if hasattr(self, "tree") else None
        if not hasattr(self, "tree"):
            return
        for item in self.tree.get_children():
            self.tree.delete(item)
        visible = self.filtered_rows()
        for category, path, detail in visible:
            ignored = self.is_ignored(path)
            iid = self.tree.insert("", "end", values=(
                "Ignoriert" if ignored else category, path, detail),
                tags=("ignored",) if ignored else ())
            if path == selected_path:
                self.tree.selection_set(iid)
        self.visible_count_var.set(f"{len(visible)} von {len(self.rows)} angezeigt")
        state = "normal" if visible and not self.scanning else "disabled"
        self.copy_button.configure(state=state)
        self.save_button.configure(state=state)
        self.update_buttons()

    def update_buttons(self, _event=None):
        selected = self.selected_path()
        state = "normal" if selected and not self.scanning else "disabled"
        self.open_button.configure(state=state)
        self.ignore_button.configure(state=state)
        self.ignore_button.configure(text="Ignorieren aufheben" if selected and self.is_ignored(selected) else "Ignorieren")

    def toggle_ignore(self):
        selected = self.selected_path()
        if not selected or self.scanning:
            return
        file_path = Path(selected)
        ignore_file = file_path.parent / "ignore.txt"
        key = self._path_key(file_path)
        updated = set(self.ignored_paths)
        if key in updated:
            updated.remove(key)
        else:
            updated.add(key)
        try:
            # Jede Ignorierliste enthält nur Dateien aus ihrem eigenen Verzeichnis.
            names = sorted(
                (Path(p).name for p in updated
                 if self._path_key(Path(p).parent) == self._path_key(file_path.parent)),
                key=str.casefold)
            temporary = ignore_file.with_name("ignore.txt.tmp")
            temporary.write_text("\n".join(names) + ("\n" if names else ""), encoding="utf-8")
            temporary.replace(ignore_file)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Ignorierliste nicht gespeichert", str(exc))
            return
        self.ignored_paths = updated
        self.apply_filter()
        self.status_var.set(f"Ignorierliste aktualisiert: {ignore_file}")

    def selected_path(self):
        selected = self.tree.selection()
        if len(selected) != 1:
            return None
        values = self.tree.item(selected[0], "values")
        return str(values[1]) if len(values) > 1 else None

    def open_selected(self):
        path = self.selected_path()
        if path:
            self.open_path(path)

    def open_result(self, event):
        row = self.tree.identify_row(event.y)
        if row:
            values = self.tree.item(row, "values")
            if len(values) > 1:
                self.open_path(str(values[1]))

    def open_path(self, path):
        if not Path(path).is_file():
            messagebox.showerror("Datei nicht gefunden", f"Datei nicht erreichbar:\n\n{path}")
            return
        try:
            if not hasattr(os, "startfile"):
                messagebox.showerror("Nicht verfügbar", "Das Öffnen über Dateizuordnung benötigt Windows.")
                return
            os.startfile(path)
        except OSError as exc:
            messagebox.showerror("Öffnen fehlgeschlagen", str(exc))

    def copy_paths(self):
        paths = [row[1] for row in self.filtered_rows()]
        if paths:
            self.clipboard_clear()
            self.clipboard_append("\n".join(paths))
            self.status_var.set(f"{len(paths)} Pfad/Pfade kopiert.")

    def save_report(self):
        visible = self.filtered_rows()
        if not visible:
            return
        destination = filedialog.asksaveasfilename(
            title="Prüfbericht speichern", defaultextension=".txt",
            filetypes=[("Textdatei", "*.txt"), ("Alle Dateien", "*.*")],
            initialfile="TB2_Negativtester_Bericht.txt")
        if not destination:
            return
        lines = ["TB2-Negativtester – Prüfbericht",
                 "Fragmente: 2 Zeichen in bekannter Datensatzstruktur; manuelle Analyse empfohlen.",
                 "Vermutlich kein Text: keine bekannten Muster oder 2-Zeichen-Fragmente.",
                 "Ein Nichttreffer beweist nicht, dass die Datei keinen Text enthält.",
                 f"Aktiver Filter: {self.filter_var.get()}",
                 f"Angezeigte Treffer: {len(visible)} von {len(self.rows)}", ""]
        lines.extend(f"{'Ignoriert' if self.is_ignored(path) else category}\t{path}\t{detail}"
                     for category, path, detail in visible)
        try:
            Path(destination).write_text("\n".join(lines) + "\n", encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("Speichern fehlgeschlagen", str(exc))
            return
        self.status_var.set(f"Bericht gespeichert: {destination}")

    def clear(self):
        self.rows = []
        self.scan_summary = ""
        self.apply_filter()
        self.copy_button.configure(state="disabled")
        self.open_button.configure(state="disabled")
        self.ignore_button.configure(state="disabled")
        self.save_button.configure(state="disabled")
        self.status_var.set("Ergebnisliste geleert.")


if __name__ == "__main__":
    App().mainloop()