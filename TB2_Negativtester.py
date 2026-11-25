#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TB2-Negativtester: prüft Dateien auf bislang bekannte TB2-Textmuster."""
from __future__ import annotations

import os
import queue
import threading
from time import perf_counter
import zipfile
import re
import webbrowser
from pathlib import Path
from tb2.tb2_version import APP_VERSION
from tb2 import tb2_ignore
from tb2.tb2_settings import load_folder, remember_folder, load_option, bind_option, load_export_folder, remember_export_folder
from tb2.tb2_project_info import PROJECT_URL, MIT_LICENSE
from tb2.tb2_muster import PROFILES, find_all, has_early_80_pattern, has_variable_80_pattern, has_wide_587_pattern, has_early_82_pattern, has_variable_98_pattern, has_variable_106_pattern, extract_counter_lines
from tb2.tb2_window_position import center_window
from tb2.tb2_changelog import changelog_for_version
from tb2.tb2_app_identity import configure_app_identity, apply_window_icon
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, font as tkfont


MIN_CHARACTERS = 3
INFO_TEXT = ("Schnell überspringt erkannte JPEG-Daten und kann Textmuster übersehen. Vollständig prüft alle Bytes. "
             "Erkannt: mindestens 3 zusammenhängende Zeichen im bekannten TB2-Muster. "
             "Fragment: 2 Zeichen in passender Struktur – könnte Text enthalten, muss analysiert werden. "
             "Ohne Treffer: enthält vermutlich keinen Text. Dies ist keine sichere Aussage; "
             "unbekannte Kodierungen können übersehen werden. Leer und Fehler werden separat gemeldet.")

_find_all = find_all


def format_number(value, decimals=0):
    """German display formatting, independent of the system locale."""
    return format(value, f",.{decimals}f").translate(str.maketrans(",.", ".,"))


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


COUNTER_REVIEW = {"Prüfen", "Unbekanntes Schriftformat", "Unbekannte Struktur"}

def counter_warning_category(warnings):
    if any("unbekannte struktur" in w.casefold() for w in warnings):
        return "Unbekannte Struktur"
    if any(w.startswith("Kein bekanntes Schriftformat gefunden:") for w in warnings):
        return "Unbekanntes Schriftformat"
    return "Prüfen"


def inspect_counter_file(path: Path, search_mode: str = "full") -> tuple[str, str]:
    """Separate Counter-Diagnose; keine Aussage über garantierte Vollständigkeit."""
    try:
        data = path.read_bytes()
    except OSError as exc:
        return "Fehler", str(exc)
    if not data:
        return "Leer", "Datei enthält 0 Bytes"
    from tb2.tb2_muster import historical_resource_document
    resources = historical_resource_document(data)
    if resources is not None:
        detail = ", ".join(f"{resources.count(kind)} {kind}"
                           for kind in ("STN", "ORN", "BAU") if kind in resources)
        return "Kein Text erkannt", f"Historisches Ressourcendokument: {detail}; keine Schriftobjekte."
    from TB2_Textcounter import counter_lines
    lines, warnings = counter_lines(data, search_mode)
    count = sum(sum(code != 0xFA for code in glyphs) for _, glyphs in lines)
    if warnings:
        return counter_warning_category(warnings), f"{format_number(len(lines))} Zeile(n), {format_number(count)} Zeichen; " + "; ".join(warnings[:3])
    if lines:
        return "Erkannt", f"{format_number(len(lines))} Zeile(n), {format_number(count)} Zeichen (Vollständigkeit nicht garantiert)"
    if has_pattern_in_mode(data, search_mode, minimum=2):
        return "Prüfen", "Bekannte Textmuster, aber keine zählbaren Textzeilen"
    return "Kein Text erkannt", "Keine bekannten Textmuster; Textfreiheit nicht bewiesen"


def has_pattern_in_mode(data, search_mode, minimum=MIN_CHARACTERS):
    if search_mode != "fast":
        return has_known_glyph_pattern(data, minimum)
    from tb2.tb2_jpeg_fast import jpeg_ranges
    previous = 0
    for start, end in jpeg_ranges(data):
        if start > previous and has_known_glyph_pattern(data[previous:start], minimum):
            return True
        previous = end
    return previous < len(data) and has_known_glyph_pattern(data[previous:], minimum)


def inspect_file(path: Path, search_mode: str = "full") -> tuple[str, str]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        return "Fehler", str(exc)
    if not data:
        return "Leer", "Datei enthält 0 Bytes"
    if has_pattern_in_mode(data, search_mode):
        return "Erkannt", "Bekanntes Muster (mindestens 3 Zeichen)"
    if has_pattern_in_mode(data, search_mode, minimum=2):
        return "Fragment", "Könnte Text enthalten, muss analysiert werden"
    return "Vermutlich kein Text", "Enthält vermutlich keinen Text"


class App(tk.Tk):
    def __init__(self):
        configure_app_identity("ropaha.TB2Negativtester")
        super().__init__()
        apply_window_icon(self)
        self.title(f"TB2-Negativtester – {APP_VERSION}")
        center_window(self, 900, 560)
        self.minsize(800, 480)
        self.events: queue.Queue = queue.Queue()
        self.scanning = False
        self.exporting = False
        self.cancel_scan_event = threading.Event()
        self.exit_after_scan = False
        self.protocol("WM_DELETE_WINDOW", self.request_exit)
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
        self.scan_totals = None
        self.access_issues = []
        self._build_ui()
        self.folder_var.trace_add("write", self._update_scan_button)
        self._update_scan_button()
        self.after(100, self._poll_events)

    def _build_ui(self):
        frame = ttk.Frame(self, padding=14)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Zu prüfender Ordner:").grid(row=0, column=0, sticky="w")
        self.folder_var = tk.StringVar(value=load_folder())
        self.folder_entry = ttk.Entry(frame, textvariable=self.folder_var)
        self.folder_entry.grid(row=0, column=1, sticky="ew", padx=10)
        self.folder_button = ttk.Button(frame, text="Ordner wählen …", command=self.choose_folder)
        self.folder_button.grid(row=0, column=2)
        self.mode_var = tk.StringVar(value="Textfinder-Prüfung")
        ttk.Label(frame, text="Prüfmodus:").grid(row=1, column=0, sticky="w")
        self.mode_box = ttk.Combobox(frame, textvariable=self.mode_var,
                                     state="readonly", width=27,
                                     values=("Textfinder-Prüfung", "Textcounter-Prüfung"))
        self.mode_box.grid(row=1, column=1, sticky="w", padx=10)
        self.recursive_var = tk.BooleanVar(value=load_option("recursive", True))
        bind_option(self.recursive_var, "recursive")
        self.recursive_check = ttk.Checkbutton(frame, text="Unterordner einbeziehen", variable=self.recursive_var)
        self.recursive_check.grid(
            row=1, column=2, sticky="w", pady=(9, 2))
        self.search_mode_var = tk.StringVar(value=load_option("search_mode", "fast"))
        bind_option(self.search_mode_var, "search_mode")
        ttk.Label(frame, text="Suchmodus:").grid(row=2, column=0, sticky="w")
        mode_options = ttk.Frame(frame)
        mode_options.grid(row=2, column=1, columnspan=2, sticky="w", padx=10, pady=(6, 2))
        self.fast_radio = ttk.Radiobutton(mode_options, text="Schnell (JPEG überspringen)", variable=self.search_mode_var, value="fast")
        self.fast_radio.pack(side="left", padx=(0, 14))
        self.full_radio = ttk.Radiobutton(mode_options, text="Vollständig (alle Bytes)", variable=self.search_mode_var, value="full")
        self.full_radio.pack(side="left")
        actions = ttk.Frame(frame)
        actions.grid(row=3, column=0, columnspan=3, sticky="w", pady=(12, 10))
        self.scan_button = ttk.Button(actions, text="Ordner prüfen", command=self.scan_or_cancel, state="disabled")
        self.scan_button.pack(side="left")
        self.issues_button = ttk.Button(
            actions, text="Zugriffsprobleme", command=self.show_access_issues)
        # Erst nach einer Prüfung mit Zugriffsproblemen sichtbar.
        self.open_button = ttk.Button(actions, text="Datei öffnen", command=self.open_selected, state="disabled")
        self.open_button.pack(side="left", padx=(8, 0))
        self.ignore_button = ttk.Button(actions, text="Ignorieren", command=self.toggle_ignore, state="disabled")
        self.ignore_button.pack(side="left", padx=(8, 0))
        self.copy_button = ttk.Button(actions, text="Pfade kopieren", command=self.copy_paths, state="disabled")
        self.copy_button.pack(side="left", padx=(8, 0))
        self.copy_row_button = ttk.Button(actions, text="Zeile kopieren", command=self.copy_selected_rows, state="disabled")
        self.copy_row_button.pack(side="left", padx=(8, 0))
        self.save_button = ttk.Button(actions, text="TXT und ZIP speichern …", command=self.save_report, state="disabled")
        self.save_button.pack(side="left", padx=(8, 0))
        self.clear_button = ttk.Button(actions, text="Leeren", command=self.clear, state="disabled")
        self.clear_button.pack(side="left", padx=(8, 0))
        self.progress = ttk.Progressbar(frame, mode="determinate")
        self.progress.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(0, 7))
        self.status_var = tk.StringVar(value="Bereit. Ordner auswählen und Prüfung starten.")
        status_frame = ttk.Frame(frame)
        status_frame.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        status_label = ttk.Label(status_frame, textvariable=self.status_var, justify="left", anchor="w")
        status_label.pack(fill="x", expand=True)
        status_frame.bind("<Configure>", lambda event: status_label.configure(wraplength=max(100, event.width - 8)))

        filters = ttk.Frame(frame)
        filters.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(3, 7))
        ttk.Label(filters, text="Trefferliste filtern:").pack(side="left", padx=(0, 9))
        self.filter_box = ttk.Combobox(filters, textvariable=self.filter_var, state="disabled",
                                       values=list(self.filter_options), width=42)
        self.filter_box.pack(side="left")
        self.mode_var.trace_add("write", self._on_mode_change)
        self.filter_box.bind("<<ComboboxSelected>>", self.apply_filter)
        self.visible_count_var = tk.StringVar(value="Noch keine Ergebnisse")
        ttk.Label(filters, textvariable=self.visible_count_var).pack(side="left", padx=(14, 0))
        results_frame = ttk.Frame(frame)
        results_frame.grid(row=7, column=0, columnspan=3, sticky="nsew")
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(results_frame, columns=("category", "path", "detail"), show="headings")
        self.tree.heading("category", text="Status")
        self.tree.heading("path", text="Dateipfad")
        self.tree.heading("detail", text="Hinweis")
        self.tree.column("category", width=150, minwidth=120, stretch=False, anchor="w")
        self.tree.column("path", width=100, minwidth=100, stretch=True, anchor="w")
        self.tree.column("detail", width=190, minwidth=130, stretch=False, anchor="w")
        self.tree.tag_configure("ignored", foreground="#777777")
        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll = ttk.Scrollbar(results_frame, orient="vertical", command=self.tree.yview)
        yscroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=yscroll.set)
        xscroll = ttk.Scrollbar(results_frame, orient="horizontal", command=self.tree.xview)
        xscroll.grid(row=1, column=0, sticky="ew")
        self.tree.configure(xscrollcommand=xscroll.set)
        self.tree.after_idle(self._fit_result_columns)
        self.tree.bind("<Double-1>", self.open_result)
        self.tree.bind("<<TreeviewSelect>>", self.update_buttons)
        self.tree.bind("<Control-c>", self.copy_selected_rows)

        footer = ttk.Frame(frame)
        footer.grid(row=8, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        ttk.Button(footer, text="Programm beenden", command=self.request_exit).pack(side="right")
        ttk.Button(footer, text="Info", command=self.show_info).pack(side="right", padx=(0, 8))

        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(7, weight=1)

    def _on_mode_change(self, *_args):
        if self.scanning or self.exporting:
            return
        counter = self.mode_var.get() == "Textcounter-Prüfung"
        self.filter_options = (
            {"Alle auffälligen Dateien": None,
             "Prüfen (Textcounter)": COUNTER_REVIEW,
             "Unbekanntes Schriftformat (Textcounter)": {"Unbekanntes Schriftformat"},
             "Unbekannte Struktur (Textcounter)": {"Unbekannte Struktur"},
             "Kein Text erkannt": {"Kein Text erkannt"},
             "Lesefehler / Leere Dateien": {"Fehler", "Leer"},
             "Ignoriert": {"Ignoriert"}}
            if counter else
            {"Alle auffälligen Dateien": None,
             "Könnte Text enthalten, muss analysiert werden": {"Fragment"},
             "Enthält vermutlich keinen Text": {"Vermutlich kein Text"},
             "Lesefehler / Leere Dateien": {"Fehler", "Leer"},
             "Ignoriert": {"Ignoriert"}}
        )
        self.filter_box.configure(values=list(self.filter_options))
        self.filter_var.set("Alle auffälligen Dateien")
        self.rows = []
        self.scan_totals = None
        self.scan_summary = ""
        self.apply_filter()
        self.status_var.set("Prüfmodus gewechselt. Bitte Ordner erneut prüfen.")

    def show_info(self):
        """Show application details and the former footer help text."""
        dialog = tk.Toplevel(self)
        dialog.title("Info – TB2-Negativtester")
        center_window(dialog, 650, 380, parent=self)
        dialog.minsize(480, 300)
        dialog.transient(self)
        body = ttk.Frame(dialog, padding=18)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text=f"{'TB2-Negativtester'} – Version {APP_VERSION}",
                  font=("TkDefaultFont", 13, "bold")).pack(anchor="w", pady=(0, 12))
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
        dialog.title(f"Was ist neu? – TB2-Negativtester {APP_VERSION}")
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
        dialog.title("MIT-Lizenz – TB2-Negativtester")
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
        """Alle übersprungenen Verzeichnisse/Listen bei Bedarf anzeigen."""
        if not self.access_issues:
            return
        dialog = tk.Toplevel(self)
        dialog.title("Zugriffsprobleme – TB2-Negativtester")
        center_window(dialog, 780, 500, parent=self)
        dialog.minsize(480, 300)
        dialog.transient(self)
        body = ttk.Frame(dialog, padding=14)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text=f"{format_number(len(self.access_issues))} übersprungene Verzeichnisse/Listen",
                  font=("TkDefaultFont", 12, "bold")).pack(anchor="w", pady=(0, 10))
        text_frame = ttk.Frame(body)
        text_frame.pack(fill="both", expand=True)
        details = tk.Text(text_frame, wrap="word", font=("TkDefaultFont", 10),
                          padx=8, pady=8)
        details.insert("1.0", "\n\n".join(self.access_issues))
        details.configure(state="disabled")
        details.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=details.yview)
        scrollbar.pack(side="right", fill="y")
        details.configure(yscrollcommand=scrollbar.set)
        ttk.Button(body, text="Schließen", command=dialog.destroy).pack(
            anchor="e", pady=(10, 0))

    def choose_folder(self):
        folder = filedialog.askdirectory(title="Ordner mit TB2-/TBL-Dateien auswählen", initialdir=self.folder_var.get() or None)
        if folder:
            self.folder_var.set(folder)
            remember_folder(folder)

    def _update_scan_button(self, *_args):
        """Ordner prüfen anbieten oder laufende Prüfung abbrechbar halten."""
        if self.scanning or self.exporting:
            if self.exporting:
                self.scan_button.configure(state="disabled")
                return
            if self.cancel_scan_event.is_set():
                self.scan_button.configure(state="disabled", text="Abbruch läuft …")
            else:
                self.scan_button.configure(state="normal", text="Prüfung abbrechen")
        else:
            self.scan_button.configure(
                state="normal" if self.folder_var.get().strip() else "disabled",
                text="Ordner prüfen")

    def request_exit(self):
        """Während einer Prüfung Rückfrage stellen und kontrolliert beenden."""
        if self.exporting:
            messagebox.showinfo("Export läuft", "Bitte warten, bis TXT und ZIP gespeichert sind.")
            return
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
        self._update_scan_button()
        self.status_var.set("Programm wird nach Abbruch der laufenden Arbeit beendet …")

    def scan_or_cancel(self):
        """Prüfung starten oder kooperativen Abbruch anfordern."""
        if self.scanning:
            if not self.cancel_scan_event.is_set():
                self.cancel_scan_event.set()
                self._update_scan_button()
                self.status_var.set("Abbruch angefordert – laufender Verzeichniszugriff bzw. aktuelle Datei wird abgeschlossen …")
            return
        self.start_scan()

    def _set_inputs_locked(self, locked):
        for widget in (self.folder_entry, self.folder_button, self.recursive_check, self.fast_radio, self.full_radio):
            widget.configure(state="disabled" if locked else "normal")
        self.mode_box.configure(state="disabled" if locked else "readonly")
        self.filter_box.configure(state="disabled" if locked or not self.rows else "readonly")

    def start_scan(self):
        folder_text = self.folder_var.get().strip()
        if not folder_text or not Path(folder_text).is_dir():
            messagebox.showwarning("Ordner fehlt", "Bitte einen gültigen Ordner auswählen.")
            return
        if self.scanning:
            return
        remember_folder(folder_text)
        self.scan_root = Path(folder_text).resolve()
        self.cancel_scan_event.clear()
        self.scan_started_at = perf_counter()
        self.scanning = True
        self._set_inputs_locked(True)
        self.rows = []
        self.ignored_paths = set()
        self.scan_summary = ""
        self.scan_totals = None
        self.scan_search_mode = self.search_mode_var.get()
        self.access_issues = []
        self.issues_button.pack_forget()
        self.clear_button.configure(state="disabled")
        self.apply_filter()
        self._update_scan_button()
        self.copy_button.configure(state="disabled")
        self.copy_row_button.configure(state="disabled")
        self.save_button.configure(state="disabled")
        self.open_button.configure(state="disabled")
        self.ignore_button.configure(state="disabled")
        self.progress.configure(mode="indeterminate", value=0)
        self.progress.start(12)
        self.status_var.set("Durchsuche Verzeichnisstruktur nach TB2-/TBL-Dateien …")
        threading.Thread(target=self._worker, args=(Path(folder_text), self.recursive_var.get(),
                                                    self.mode_var.get(), self.search_mode_var.get()),
                         daemon=True).start()

    def _worker(self, root: Path, recursive: bool, mode: str, search_mode: str):
        """Dateisuche, Ignorierlisten und Prüfung vollständig außerhalb der GUI."""
        files = []
        ignored = set()
        skipped = []
        checked_dirs = 0

        def on_walk_error(exc):
            skipped.append(f"{exc.filename or 'Unbekannter Ordner'}: {exc}")

        try:
            if recursive:
                directories = os.walk(root, topdown=True, followlinks=False,
                                      onerror=on_walk_error)
            else:
                # Dieselbe Ereignisstruktur für die Suche ohne Unterordner.
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
                checked_dirs += 1
                # Windows-Junctions/Reparse-Points nicht rekursiv durchlaufen.
                if recursive:
                    subdirs[:] = [name for name in subdirs
                                  if not os.path.isjunction(os.path.join(directory, name))]
                for name in names:
                    if name.lower().endswith((".tb2", ".tbl")):
                        files.append(Path(directory) / name)
                if checked_dirs % 50 == 0:
                    self.events.put(("discovery", checked_dirs, len(files)))
            ignore_data = tb2_ignore.load()
            if not self.cancel_scan_event.is_set():
                tb2_ignore.import_legacy(ignore_data, {path.parent for path in files},
                                         root, self.cancel_scan_event, skipped)
            self.events.put(("discovery_done", len(files), checked_dirs))
            flagged = []
            recognized = errors = empty = fragments = probably_no_text = 0
            processed = 0
            for index, path in enumerate(files, start=1):
                if self.cancel_scan_event.is_set():
                    break
                category, detail = (inspect_counter_file(path, search_mode) if mode == "Textcounter-Prüfung"
                                    else inspect_file(path, search_mode))
                processed = index
                if category not in ("Erkannt", "Fehler"):
                    try:
                        if tb2_ignore.matching(ignore_data, path):
                            ignored.add(self._path_key(path))
                    except OSError as exc:
                        skipped.append(f"{path}: {exc}")
                if category == "Erkannt":
                    recognized += 1
                else:
                    flagged.append((category, str(path.absolute()), detail))
                    if category == "Fehler":
                        errors += 1
                    elif category == "Leer":
                        empty += 1
                    elif category == "Fragment" or category in COUNTER_REVIEW:
                        fragments += 1
                    elif category in ("Vermutlich kein Text", "Kein Text erkannt"):
                        probably_no_text += 1
                self.events.put(("progress", index, len(files), path.name))
            self.events.put(("finished", flagged, processed, len(files), recognized,
                             fragments, probably_no_text, empty, errors,
                             self.cancel_scan_event.is_set(), ignored, skipped, checked_dirs,
                             perf_counter() - self.scan_started_at))
        except Exception as exc:
            self.events.put(("worker_error", str(exc)))

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
                    _, total, directories = event
                    self.progress.stop()
                    self.progress.configure(mode="determinate", maximum=max(total, 1), value=0)
                    if not self.cancel_scan_event.is_set():
                        self.status_var.set(
                            f"Dateisuche abgeschlossen: {format_number(directories)} Ordner, "
                            f"{format_number(total)} TB2-/TBL-Datei(en). Prüfung läuft …")
                elif event[0] == "progress":
                    _, current, total, name = event
                    self.progress.configure(value=current)
                    if not self.cancel_scan_event.is_set():
                        self.status_var.set(f"Datei {format_number(current)}/{format_number(total)}: {name}")
                elif event[0] == "finished":
                    if self.exit_after_scan:
                        self.destroy()
                        return
                    (_, flagged, processed, total, recognized, fragments,
                     probably_no_text, empty, errors, cancelled,
                     ignored, skipped, checked_dirs, self.scan_elapsed) = event
                    self.scan_cancelled = cancelled
                    self.scan_discovered = total
                    self.progress.stop()
                    self.ignored_paths = ignored
                    self.rows = flagged
                    self.scanning = False
                    self._set_inputs_locked(False)
                    self.apply_filter()
                    self._update_scan_button()
                    self.scan_totals = (processed, recognized, fragments,
                                        probably_no_text, empty, errors)
                    self._refresh_scan_summary()
                    if not cancelled and not total:
                        self.scan_summary = (f"Keine TB2-/TBL-Dateien gefunden ({format_number(checked_dirs)} Ordner durchsucht)."
                                             f" | Dauer: {format_number(self.scan_elapsed, 2)} s")
                        self.status_var.set(self.scan_summary)
                    self.access_issues = skipped
                    if skipped:
                        self.issues_button.configure(
                            text=f"Zugriffsprobleme ({format_number(len(skipped))})")
                        self.issues_button.pack(side="left", padx=(8, 0), after=self.scan_button)
                elif event[0] == "export_progress":
                    _, current, total = event
                    self.status_var.set(f"Diagnose-ZIP: {format_number(current)}/{format_number(total)} Dateien verarbeitet …")
                elif event[0] == "export_done":
                    _, result, error = event
                    self.exporting = False
                    self._set_inputs_locked(False)
                    self._update_scan_button()
                    self.apply_filter()
                    if error:
                        messagebox.showerror("Export fehlgeschlagen", error)
                    else:
                        self.status_var.set(result)
                        messagebox.showinfo("Export abgeschlossen", result)
                elif event[0] == "worker_error":
                    if self.exit_after_scan:
                        self.destroy()
                        return
                    self.progress.stop()
                    self.scanning = False
                    self._set_inputs_locked(False)
                    self.apply_filter()
                    self._update_scan_button()
                    messagebox.showerror("Prüfung fehlgeschlagen", event[1])
        except queue.Empty:
            pass
        self.after(100, self._poll_events)

    def _refresh_scan_summary(self):
        """Gesamtzahlen und ignorierte Einträge je Ergebniskategorie anzeigen."""
        if self.scan_totals is None:
            return
        total, recognized, fragments, probably_no_text, empty, errors = self.scan_totals
        prefix = (f"Abgebrochen: {format_number(total)}/{format_number(self.scan_discovered)}"
                  if self.scan_cancelled else f"Fertig: {format_number(total)}")
        duration = f" | Dauer: {format_number(self.scan_elapsed, 2)} s"
        ignored = {"Fragment": 0, "Vermutlich kein Text": 0,
                   "Prüfen": 0, "Unbekanntes Schriftformat": 0, "Unbekannte Struktur": 0,
                   "Kein Text erkannt": 0,
                   "Leer": 0, "Fehler": 0}
        for category, path, _ in self.rows:
            if category in ignored and self.is_ignored(path):
                ignored[category] += 1
        if self.mode_var.get() == "Textcounter-Prüfung":
            review_counts = {category: sum(row[0] == category for row in self.rows)
                             for category in COUNTER_REVIEW}
            review_ignored = sum(ignored[category] for category in COUNTER_REVIEW)
            self.scan_summary = (
                f"{prefix} Datei(en) geprüft | {format_number(recognized)} gezählt" + duration + "\n" +
                f"{format_number(fragments)} prüfen ({format_number(review_ignored)} ignoriert) | "
                f"{format_number(probably_no_text)} kein Text erkannt "
                f"({format_number(ignored['Kein Text erkannt'])} ignoriert) | "
                f"{format_number(empty)} leer | {format_number(errors)} Lesefehler\n" +
                " | ".join(f"{format_number(review_counts[category])} {category} "
                           f"({format_number(ignored[category])} ignoriert)"
                           for category in ("Unbekanntes Schriftformat", "Unbekannte Struktur", "Prüfen")))
            self.status_var.set(self.scan_summary)
            return
        self.scan_summary = (
            f"{prefix} Datei(en) geprüft | {format_number(recognized)} erkannt" + duration + "\n" +
            f"{format_number(fragments)} Fragmente ({format_number(ignored['Fragment'])} ignoriert) | "
            f"{format_number(probably_no_text)} vermutlich ohne Text "
            f"({format_number(ignored['Vermutlich kein Text'])} ignoriert) | "
            f"{format_number(empty)} leer ({format_number(ignored['Leer'])} ignoriert) | "
            f"{format_number(errors)} Lesefehler ({format_number(ignored['Fehler'])} ignoriert)")
        self.status_var.set(self.scan_summary)

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
        selected_paths = set(self.selected_paths()) if hasattr(self, "tree") else set()
        if not hasattr(self, "tree"):
            return
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.filter_box.configure(state="readonly" if self.rows and not self.scanning and not self.exporting else "disabled")
        visible = self.filtered_rows()
        for category, path, detail in visible:
            ignored = self.is_ignored(path)
            iid = self.tree.insert("", "end", values=(
                "Ignoriert" if ignored else category, path, detail),
                tags=("ignored",) if ignored else ())
            if path in selected_paths:
                self.tree.selection_add(iid)
        self.visible_count_var.set(f"{format_number(len(visible))} von {format_number(len(self.rows))} angezeigt")
        self.clear_button.configure(state="normal" if self.rows and not self.scanning and not self.exporting else "disabled")
        self._fit_result_columns(visible)
        state = "normal" if self.rows and not self.scanning and not self.exporting else "disabled"
        self.copy_button.configure(state=state)
        self.save_button.configure(state=state)
        self.update_buttons()

    def _fit_result_columns(self, rows=None):
        """Alle drei Spalten an die aktuell sichtbaren Inhalte anpassen."""
        if rows is None:
            rows = self.filtered_rows()
        style = ttk.Style(self)
        font_name = style.lookup("Treeview", "font") or "TkDefaultFont"
        font = (tkfont.nametofont(font_name)
                if isinstance(font_name, str) and font_name in tkfont.names(self)
                else tkfont.nametofont("TkDefaultFont"))
        headings = {"category": "Status", "path": "Dateipfad", "detail": "Hinweis"}
        values = {
            "category": ["Ignoriert" if self.is_ignored(path) else category
                         for category, path, detail in rows],
            "path": [path for category, path, detail in rows],
            "detail": [detail for category, path, detail in rows],
        }
        for column in ("category", "path", "detail"):
            heading_width = font.measure(headings[column]) + 32
            content_width = max((font.measure(str(value)) for value in values[column]),
                                default=0) + 24
            self.tree.column(column, width=max(heading_width, content_width, 80),
                             stretch=(column == "path"))

    def selected_paths(self):
        """Dateipfade aller ausgewählten Zeilen, auch bei Mehrfachauswahl."""
        paths = []
        for item in self.tree.selection():
            values = self.tree.item(item, "values")
            if len(values) > 1:
                paths.append(str(values[1]))
        return paths

    def update_buttons(self, _event=None):
        paths = self.selected_paths()
        self.open_button.configure(
            state="normal" if len(paths) == 1 and not self.scanning else "disabled")
        states = {self.is_ignored(path) for path in paths}
        uniform = bool(paths) and len(states) == 1 and not self.scanning
        self.copy_row_button.configure(state="normal" if paths and not self.scanning else "disabled")
        self.ignore_button.configure(
            state="normal" if uniform else "disabled",
            text="Ignorieren aufheben" if uniform and True in states else "Ignorieren")

    def copy_selected_rows(self, _event=None):
        """Vollstaendige Ergebniszeilen einschliesslich ungekürztem Hinweis kopieren."""
        selected = self.tree.selection()
        lines = []
        for item in selected:
            values = self.tree.item(item, "values")
            if len(values) == 3:
                lines.append("\t".join(map(str, values)))
        if lines:
            self.clipboard_clear()
            self.clipboard_append("\n".join(lines))
            self.status_var.set(f"{format_number(len(lines))} vollständige Ergebniszeile(n) kopiert.")

    def toggle_ignore(self):
        paths = self.selected_paths()
        states = {self.is_ignored(path) for path in paths}
        if self.scanning or not paths or len(states) != 1:
            return
        should_ignore = True not in states
        try:
            tb2_ignore.toggle(paths, should_ignore, self.scan_root)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Ignorierliste nicht gespeichert", str(exc))
            return
        keys = {self._path_key(Path(path)) for path in paths}
        self.ignored_paths = (self.ignored_paths | keys if should_ignore
                              else self.ignored_paths - keys)
        self.apply_filter()
        self._refresh_scan_summary()

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
            self.status_var.set(f"{format_number(len(paths))} Pfad/Pfade kopiert.")

    def _report_text(self):
        """Der vollständige Bericht bleibt unabhängig von Filter und ZIP-Limit."""
        mode = self.mode_var.get()
        lines = [
            f"TB2-Negativtester – vollständiger Prüfbericht ({mode})",
            f"Prüfmodus: {mode}",
            "Suchmodus: " + ("Schnell (JPEG überspringen)" if self.scan_search_mode == "fast" else "Vollständig (alle Bytes)"),
            f"Ordner: {self.folder_var.get()}",
            f"Unterordner einbeziehen: {'Ja' if self.recursive_var.get() else 'Nein'}",
            f"Gesamtzahl auffälliger Einträge: {format_number(len(self.rows))}",
            f"GUI-Filter (nur Anzeige): {self.filter_var.get()}",
            f"Zusammenfassung: {self.scan_summary or 'Keine Zusammenfassung verfügbar'}",
            "Hinweis: 'Erkannt' garantiert keine vollständige Texterkennung.",
            "Ein Nichttreffer beweist nicht, dass die Datei keinen Text enthält.",
            "",
            "Status\tDateipfad\tHinweis",
        ]
        lines.extend(
            f"{'Ignoriert (' + category + ')' if self.is_ignored(path) else category}\t{path}\t{detail}"
            for category, path, detail in self.rows
        )
        if self.access_issues:
            lines.extend(["", f"Zugriffsprobleme ({format_number(len(self.access_issues))}):"])
            lines.extend(self.access_issues)
        return "\n".join(lines) + "\n"

    def save_report(self):
        """Speichert TXT und eine größenbegrenzte Diagnose-ZIP nach DSGVO-Hinweis."""
        if self.scanning or self.exporting or self.scan_totals is None:
            return
        consent = messagebox.askyesno(
            "Datenschutzhinweis – Export",
            "Die von Ihnen exportierten Daten könnten personenbezogene Daten "
            "enthalten.\n\nSind Sie sicher, dass Sie die Funktion ausführen "
            "möchten?\n\nEine unzulässige Verarbeitung oder Weitergabe "
            "könnte gegen die Datenschutz-Grundverordnung (DSGVO) verstoßen.",
            icon="warning", default="no", parent=self)
        if not consent:
            return
        destination = filedialog.asksaveasfilename(
            title="TXT und Diagnose-ZIP speichern", defaultextension=".txt",
            filetypes=[("Textdatei", "*.txt")],
            initialfile="TB2_Negativtester_Bericht.txt", initialdir=load_export_folder() or None, parent=self)
        if not destination:
            return
        txt_path = Path(destination).with_suffix(".txt")
        zip_path = txt_path.with_suffix(".zip")
        if zip_path.exists() and not messagebox.askyesno(
                "ZIP überschreiben?",
                f"Die ZIP-Datei existiert bereits:\n{zip_path}\n\nÜberschreiben?",
                icon="warning", default="no", parent=self):
            return
        report = self._report_text()
        rows = list(self.rows)
        root = Path(self.folder_var.get()).resolve()
        self.exporting = True
        self._set_inputs_locked(True)
        self._update_scan_button()
        self.apply_filter()
        self.status_var.set("TXT und Diagnose-ZIP werden erstellt …")
        threading.Thread(
            target=self._export_worker,
            args=(txt_path, zip_path, report, rows, root),
            daemon=True).start()

    def _export_worker(self, txt_path, zip_path, report, rows, root):
        """ZIP mit max. 300 Dateien / 100 MiB Originaldaten, ohne erneuten Scan."""
        max_files = 300
        max_bytes = 100 * 1024 * 1024
        selected = []
        skipped = []
        used_bytes = 0
        try:
            # Null-Erkennungen priorisieren, dann andere Prüffälle.
            # Innerhalb einer Gruppe Jahrgänge mischen, statt einen Jahrgang
            # vollständig vor dem nächsten zu exportieren.
            def priority(row):
                detail = row[2]
                return 0 if ("0 Zeile(n), 0 Zeichen" in detail or
                             row[0] in ("Kein Text erkannt", "Vermutlich kein Text")) else 1

            def year(row):
                parts = Path(row[1]).parts
                for part in parts:
                    if re.fullmatch(r"(19|20)\d{2}", part):
                        return part
                return "Sonstige"

            buckets = {}
            for row in rows:
                if row[0] in ("Fehler", "Leer") or self._path_key(Path(row[1])) in self.ignored_paths:
                    continue
                buckets.setdefault((priority(row), year(row)), []).append(row)
            # Beide Diagnosegruppen abwechselnd berücksichtigen:
            # Null-Erkennungen und Teilzählungen/Warnungen. Die bisherige
            # Sortierung exportierte praktisch nur Null-Erkennungen.
            groups = {}
            for p in (0, 1):
                keys = sorted(k for k in buckets if k[0] == p)
                group = []
                while any(buckets[k] for k in keys):
                    for k in keys:
                        if buckets[k]:
                            group.append(buckets[k].pop(0))
                groups[p] = group
            ordered = []
            while groups[0] or groups[1]:
                for p in (0, 1):
                    if groups[p]:
                        ordered.append(groups[p].pop(0))

            zip_tmp = zip_path.with_name(zip_path.name + ".tmp")
            txt_path.write_text(report, encoding="utf-8")
            try:
                with zipfile.ZipFile(zip_tmp, "w", compression=zipfile.ZIP_DEFLATED,
                                     compresslevel=6, allowZip64=True) as archive:
                    archive.writestr("Pruefbericht.txt", report)
                    for index, (category, filename, detail) in enumerate(ordered, 1):
                        path = Path(filename)
                        try:
                            relative = path.resolve().relative_to(root)
                            if not path.is_file() or path.is_symlink():
                                raise OSError("Datei fehlt oder ist ein symbolischer Link")
                            size = path.stat().st_size
                            if len(selected) >= max_files:
                                skipped.append((filename, "Dateianzahl-Limit erreicht"))
                            elif size > max_bytes - used_bytes:
                                skipped.append((filename, "Größenlimit erreicht"))
                            else:
                                arcname = "Dateien/" + relative.as_posix()
                                archive.write(path, arcname)
                                selected.append((filename, arcname, size))
                                used_bytes += size
                        except (OSError, ValueError) as exc:
                            skipped.append((filename, str(exc)))
                        if index % 10 == 0 or index == len(ordered):
                            self.events.put(("export_progress", index, len(ordered)))
                    manifest = [
                        "TB2-Negativtester – Diagnosepaket",
                        f"Enthaltene TB2/TBL-Dateien: {format_number(len(selected))} (maximal {format_number(max_files)})",
                        f"Originaldaten: {format_number(used_bytes)} Byte (Limit {format_number(max_bytes)} Byte)",
                        f"Nicht enthalten: {format_number(len(skipped))}",
                        "Vollständiger Prüfbericht: Pruefbericht.txt",
                        "",
                        "ENTHALTEN\tZIP-Pfad\tOriginalpfad\tBytes",
                    ]
                    manifest.extend(f"ENTHALTEN\t{arc}\t{src}\t{size}"
                                    for src, arc, size in selected)
                    manifest.append("")
                    manifest.append("NICHT ENTHALTEN\tOriginalpfad\tGrund")
                    manifest.extend(f"NICHT ENTHALTEN\t{src}\t{reason}"
                                    for src, reason in skipped)
                    archive.writestr("ZIP_Inhalt.txt", "\n".join(manifest) + "\n")
                zip_tmp.replace(zip_path)
            finally:
                if zip_tmp.exists():
                    zip_tmp.unlink()
            result = (f"TXT und ZIP gespeichert: {format_number(len(rows))} Berichtszeilen, "
                      f"{format_number(len(selected))} Dateien im ZIP, {format_number(len(skipped))} nicht aufgenommen.\n"
                      f"TXT: {txt_path}\nZIP: {zip_path}")
            remember_export_folder(txt_path.resolve().parent)
            self.events.put(("export_done", result, None))
        except (OSError, ValueError, zipfile.BadZipFile) as exc:
            self.events.put(("export_done", None, str(exc)))

    def clear(self):
        if self.scanning or not self.rows:
            return
        self.rows = []
        self.clear_button.configure(state="disabled")
        self.scan_summary = ""
        self.apply_filter()
        self.copy_button.configure(state="disabled")
        self.open_button.configure(state="disabled")
        self.ignore_button.configure(state="disabled")
        self.save_button.configure(state="disabled")
        self.status_var.set("Ergebnisliste geleert.")


if __name__ == "__main__":
    App().mainloop()