#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TB2-Textfinder 1.8.8

Durchsucht .TB2-Dateien nach lesbarem Text und bislang beobachteten
SignumNext-Glyphenprofilen mehrerer Formatgenerationen. Treffer werden
als vollständige Dateipfade ausgegeben; interne Offsets bleiben verborgen.
"""
from __future__ import annotations

import os
import queue
import threading
import webbrowser
from time import perf_counter
from tb2_version import APP_VERSION
from tb2_settings import load_folder, remember_folder, load_option, bind_option
from tb2_project_info import PROJECT_URL, MIT_LICENSE
from tb2_muster import PROFILES, find_all, has_early_80_pattern, has_variable_80_pattern, has_wide_587_pattern, has_early_82_pattern, has_variable_98_pattern, has_variable_106_pattern
from tb2_muster import (_early_80_record, _variable_marker_record, _wide_587_record, _early_82_record, _variable_98_record, _variable_106_record)
from tb2_resource_paths import mask_resource_paths
from tb2_whole_words import contains_whole_word
from pathlib import Path
from tb2_window_position import center_window
from tb2_changelog import changelog_for_version
from tb2_app_identity import configure_app_identity, apply_window_icon
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, font as tkfont

APP_TITLE = "TB2-Textfinder"


INFO_TEXT = (
    "Schnell überspringt JPEG-Daten und kann Treffer übersehen; Vollständig entspricht der bisherigen Suche. "
    "Datei in der Trefferliste markieren und auf 'Datei öffnen' klicken – "
    "oder den Treffer doppelt anklicken. Die TB2-Datei wird mit dem in Windows "
    "verknüpften Programm geöffnet. Suche in Klartext sowie in untersuchten TB2-Glyphenmustern mehrerer Generationen "
    "(Datensatzabstände 80, 98, 106 und 587 Byte, mit unterschiedlichen Markern). Umlaute und weitere Ein-Byte-Zeichen werden "
    "berücksichtigt. Die Groß-/Kleinschreibung wird standardmäßig ignoriert – auch bei "
    "Umlauten. Die Dateiformate werden weiter untersucht; ein Nichttreffer ist daher "
    "noch kein Beweis, dass der Text fehlt. Die experimentelle Ganzwortsuche "
    "prüft Wortgrenzen in bekannten Datenmustern; bei unbekannten Formaten "
    "kann sie Treffer übersehen. Bindestriche gelten als Wortgrenzen."
)

_find_all = find_all


def format_number(value, decimals=0):
    """German display formatting, independent of the system locale."""
    return format(value, f",.{decimals}f").translate(str.maketrans(",.", ".,"))


def _plain_needles(term: str, case_sensitive: bool) -> list[bytes]:
    variants = [term]
    if not case_sensitive:
        variants.extend([term.lower(), term.upper(), term.title()])
    needles: list[bytes] = []
    seen: set[bytes] = set()
    for variant in variants:
        for encoding in ("utf-8", "utf-16le"):
            try:
                raw = variant.encode(encoding)
            except UnicodeEncodeError:
                continue
            if raw and raw not in seen:
                seen.add(raw)
                needles.append(raw)
        try:
            raw = variant.encode("latin-1")
        except UnicodeEncodeError:
            continue
        if raw and raw not in seen:
            seen.add(raw)
            needles.append(raw)
    return needles


def _glyph_char_codes(char: str, case_sensitive: bool) -> set[int]:
    """Return possible one-byte character codes used by older TB2 text records.

    SignumNext examples show OEM code-page values (for example ä = 0x84),
    so ASCII-only matching is insufficient. We test common German/Windows
    single-byte encodings while retaining the original character positions.
    """
    variants = {char}
    if not case_sensitive:
        lower = char.lower()
        upper = char.upper()
        if len(lower) == 1:
            variants.add(lower)
        if len(upper) == 1:
            variants.add(upper)

    codes: set[int] = set()
    for variant in variants:
        for encoding in ("cp850", "cp437", "cp1252", "latin-1"):
            try:
                raw = variant.encode(encoding)
            except UnicodeEncodeError:
                continue
            if len(raw) == 1:
                codes.add(raw[0])
    if char == " ":
        codes.add(0xFA)  # Leerzeichen in älteren Signum-Glyphenfolgen
    return codes


def _matches_glyph_profile(data: bytes, term: str, marker: bytes,
                           stride: int, case_sensitive: bool, marker_offset: int = 1) -> bool:
    """Check one character per record with the selected record spacing."""
    if not term:
        return False

    char_codes = [_glyph_char_codes(ch, case_sensitive) for ch in term]
    if any(not codes for codes in char_codes):
        return False

    # Locate possible first records, then verify each character's encoded byte.
    for first_code in char_codes[0]:
        if marker_offset == 1:
            candidates = _find_all(data, bytes([first_code]) + marker)
        else:
            candidates = (pos - marker_offset for pos in _find_all(data, marker)
                          if pos >= marker_offset and data[pos - marker_offset] == first_code)
        for start in candidates:
            matched = True
            for index, allowed_codes in enumerate(char_codes):
                pos = start + index * stride
                if pos + marker_offset + len(marker) > len(data):
                    matched = False
                    break
                if data[pos] not in allowed_codes:
                    matched = False
                    break
                if data[pos + marker_offset:pos + marker_offset + len(marker)] != marker:
                    matched = False
                    break
            if matched:
                return True
    return False



def _matches_early_80(data: bytes, term: str, case_sensitive: bool) -> bool:
    if not term:
        return False
    codes = [_glyph_char_codes(ch, case_sensitive) for ch in term]
    if any(not c for c in codes):
        return False
    for marker_pos in _find_all(data, b"\x80"):
        start = marker_pos - 1
        if start < 0 or data[start] not in codes[0]:
            continue
        if start + (len(codes) - 1) * 80 + 8 > len(data):
            continue
        if all(data[start + i * 80] in allowed
               and _early_80_record(data, start + i * 80)
               for i, allowed in enumerate(codes)):
            return True
    return False


def _matches_variable_80(data: bytes, term: str, case_sensitive: bool) -> bool:
    if not term:
        return False
    codes = [_glyph_char_codes(ch, case_sensitive) for ch in term]
    if any(not c for c in codes):
        return False
    # Marker als Anker, statt alle Bytepositionen zu durchsuchen.
    for marker_pos in _find_all(data, b"\x81"):
        start = marker_pos - 1
        if start < 0 or data[start] not in codes[0]:
            continue
        if all(pos + 8 <= len(data)
               and data[pos] in allowed
               and _variable_marker_record(data, pos)
               for pos, allowed in ((start + i * 80, c) for i, c in enumerate(codes))):
            return True
    return False


def _matches_wide_587(data: bytes, term: str, case_sensitive: bool) -> bool:
    if not term:
        return False
    codes = [_glyph_char_codes(ch, case_sensitive) for ch in term]
    if any(not c for c in codes):
        return False
    for marker in (b"\x7e", b"\x7f", b"\x80", b"\x81", b"\x84"):
        for marker_pos in _find_all(data, marker):
            start = marker_pos - 1
            if start < 0 or data[start] not in codes[0]:
                continue
            last = start + (len(codes) - 1) * 587
            if last + 8 > len(data):
                continue
            if all(data[start + i * 587] in allowed
                   and _wide_587_record(data, start + i * 587)
                   for i, allowed in enumerate(codes)):
                return True
    return False


def _matches_early_82(data: bytes, term: str, case_sensitive: bool) -> bool:
    if not term:
        return False
    codes = [_glyph_char_codes(ch, case_sensitive) for ch in term]
    if any(not c for c in codes):
        return False
    for marker_pos in _find_all(data, b"\x82"):
        start = marker_pos - 1
        if start < 0 or data[start] not in codes[0]:
            continue
        if start + (len(codes) - 1) * 80 + 8 > len(data):
            continue
        if all(data[start + i * 80] in allowed
               and _early_82_record(data, start + i * 80)
               for i, allowed in enumerate(codes)):
            return True
    return False


def _matches_variable_98(data: bytes, term: str, case_sensitive: bool) -> bool:
    if not term:
        return False
    codes = [_glyph_char_codes(ch, case_sensitive) for ch in term]
    if any(not c for c in codes):
        return False
    for marker in (b"\x80", b"\x81"):
        for marker_pos in _find_all(data, marker):
            start = marker_pos - 1
            if start < 0 or data[start] not in codes[0]:
                continue
            if start + (len(codes) - 1) * 98 + 8 > len(data):
                continue
            if all(data[start + i * 98] in allowed
                   and _variable_98_record(data, start + i * 98)
                   for i, allowed in enumerate(codes)):
                return True
    return False


def _matches_variable_106(data: bytes, term: str, case_sensitive: bool) -> bool:
    if not term:
        return False
    codes = [_glyph_char_codes(ch, case_sensitive) for ch in term]
    if any(not c for c in codes):
        return False
    for marker in (b"\x81", b"\x82"):
        for marker_pos in _find_all(data, marker):
            start = marker_pos - 1
            if start < 0 or data[start] not in codes[0]:
                continue
            if start + (len(codes) - 1) * 106 + 10 > len(data):
                continue
            if all(data[start + i * 106] in allowed
                   and _variable_106_record(data, start + i * 106)
                   for i, allowed in enumerate(codes)):
                return True
    return False


def _matches_legacy_mixed_records(data: bytes, term: str, case_sensitive: bool) -> bool:
    """1990s Signum glyphs retained in SignumNext files.

    Observed in 9300061.TB2 (80-byte records) and its edited 2026 copy
    (106-byte records). The first glyph has 82 + variable five bytes +
    81 00 00; following glyphs have 82 + variable five bytes +
    80 XX YY, with the same XX YY pair throughout a word.
    Requiring the control-byte structure and consistent pair avoids
    matching arbitrary bytes merely because they are 80/106 apart.
    """
    if len(term) < 2:
        return False
    codes = [_glyph_char_codes(ch, case_sensitive) for ch in term]
    if any(not allowed for allowed in codes):
        return False

    for stride in (80, 106):
        for first in codes[0]:
            for start in _find_all(data, bytes((first, 0x82))):
                end = start + (len(term) - 1) * stride + 10
                if end > len(data) or data[start + 7:start + 10] != b"\x81\x00\x00":
                    continue
                pair = data[start + stride + 8:start + stride + 10]
                if not pair or len(pair) != 2:
                    continue
                if all(
                    data[pos] in allowed
                    and data[pos + 1] == 0x82
                    and data[pos + 7] == 0x80
                    and data[pos + 8:pos + 10] == pair
                    for pos, allowed in (
                        (start + i * stride, allowed)
                        for i, allowed in enumerate(codes[1:], start=1)
                    )
                ):
                    return True
    return False


def contains_term(data: bytes, term: str, case_sensitive: bool = False) -> bool:
    if any(data.find(needle) >= 0 for needle in _plain_needles(term, case_sensitive)):
        return True
    for _profile_name, marker, strides in PROFILES:
        for stride in strides:
            # Auch bei 80-Byte-Datensaetzen kommt ein variabler 6-Byte-Vorspann
            # vor (z. B. 9000143.TB2). Die Marker beginnen dann bei +7.
            offsets = (1, 7) if stride == 0x50 and marker == b"\x81\x00\x00" else ((7,) if stride == 0x62 else (1,))
            for marker_offset in offsets:
                if _matches_glyph_profile(data, term, marker, stride, case_sensitive, marker_offset):
                    return True
    return (_matches_variable_80(data, term, case_sensitive)
            or _matches_wide_587(data, term, case_sensitive)
            or _matches_early_80(data, term, case_sensitive)
            or _matches_early_82(data, term, case_sensitive)
            or _matches_variable_98(data, term, case_sensitive)
            or _matches_variable_106(data, term, case_sensitive)
            or _matches_legacy_mixed_records(data, term, case_sensitive))


def scan_file(path: Path, term: str, case_sensitive: bool, whole_word: bool = False) -> tuple[bool, str | None]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        return False, str(exc)
    data = mask_resource_paths(data)
    candidate = contains_term(data, term, case_sensitive)
    return (contains_whole_word(data, term, case_sensitive) if whole_word and candidate
            else candidate if not whole_word else False), None


class App(tk.Tk):
    def __init__(self):
        configure_app_identity("ropaha.TB2Textfinder")
        super().__init__()
        apply_window_icon(self)
        self.title(f"{APP_TITLE} – {APP_VERSION}")
        center_window(self, 800, 520)
        self.minsize(720, 420)
        self.events: queue.Queue = queue.Queue()
        self.scanning = False
        self.cancel_scan_event = threading.Event()
        self.exit_after_scan = False
        self.protocol("WM_DELETE_WINDOW", self.request_exit)
        self.result_paths: list[str] = []
        self.access_issues: list[str] = []
        self._build_ui()
        self.folder_var.trace_add("write", self._update_search_button)
        self._update_search_button()
        self.term_var.trace_add("write", self._update_search_button)
        self.after(100, self._poll_events)

    def _build_ui(self):
        frame = ttk.Frame(self, padding=14)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Gesuchter Text:").grid(row=0, column=0, sticky="w")
        self.term_var = tk.StringVar()
        self.term_entry = ttk.Entry(frame, textvariable=self.term_var, width=38)
        self.term_entry.grid(row=0, column=1, sticky="ew", padx=(10, 10))

        ttk.Label(frame, text="Ordner:").grid(row=1, column=0, sticky="w", pady=(12, 0))
        self.folder_var = tk.StringVar(value=load_folder())
        self.folder_entry = ttk.Entry(frame, textvariable=self.folder_var)
        self.folder_entry.grid(
            row=1, column=1, sticky="ew", padx=(10, 10), pady=(12, 0)
        )
        self.folder_button = ttk.Button(frame, text="Ordner wählen …", command=self.choose_folder)
        self.folder_button.grid(
            row=1, column=2, pady=(12, 0)
        )

        options = ttk.Frame(frame)
        options.grid(row=2, column=1, columnspan=2, sticky="w", pady=(10, 2))
        self.recursive_var = tk.BooleanVar(value=load_option("recursive", True))
        bind_option(self.recursive_var, "recursive")
        self.case_var = tk.BooleanVar(value=load_option("case_sensitive", False))
        bind_option(self.case_var, "case_sensitive")
        self.whole_word_var = tk.BooleanVar(value=load_option("whole_word", True))
        bind_option(self.whole_word_var, "whole_word")
        self.search_mode_var = tk.StringVar(value=load_option("search_mode", "fast"))
        bind_option(self.search_mode_var, "search_mode")
        self.recursive_check = ttk.Checkbutton(options, text="Unterordner einbeziehen", variable=self.recursive_var)
        self.recursive_check.pack(side="left", padx=(0, 20))
        self.whole_check = ttk.Checkbutton(options, text="Nur ganze Wörter", variable=self.whole_word_var)
        self.whole_check.pack(side="left", padx=(0, 20))
        self.case_check = ttk.Checkbutton(options, text="Groß-/Kleinschreibung beachten", variable=self.case_var)
        self.case_check.pack(side="left")

        mode_options = ttk.Frame(frame)
        mode_options.grid(row=3, column=1, columnspan=2, sticky="w", pady=(4, 2))
        ttk.Label(mode_options, text="Suchmodus:").pack(side="left", padx=(0, 10))
        self.fast_radio = ttk.Radiobutton(mode_options, text="Schnell (JPEG überspringen)",
                        variable=self.search_mode_var, value="fast")
        self.fast_radio.pack(side="left", padx=(0, 14))
        self.full_radio = ttk.Radiobutton(mode_options, text="Vollständig (alle Bytes)", variable=self.search_mode_var,
                        value="full")
        self.full_radio.pack(side="left")

        actions = ttk.Frame(frame)
        actions.grid(row=4, column=0, columnspan=3, sticky="w", pady=(12, 10))
        self.search_button = ttk.Button(actions, text="Suchen", command=self.search_or_cancel, state="disabled")
        self.search_button.pack(side="left")
        self.issues_button = ttk.Button(actions, text="Zugriffsprobleme", command=self.show_access_issues)
        self.open_button = ttk.Button(
            actions, text="Datei öffnen", command=self.open_selected_file, state="disabled"
        )
        self.open_button.pack(side="left", padx=(8, 0))
        self.copy_button = ttk.Button(actions, text="Pfade kopieren", command=self.copy_paths, state="disabled")
        self.copy_button.pack(side="left", padx=(8, 0))
        self.save_button = ttk.Button(actions, text="TXT speichern …", command=self.save_paths, state="disabled")
        self.save_button.pack(side="left", padx=(8, 0))
        self.clear_button = ttk.Button(actions, text="Leeren", command=self.clear_results, state="disabled")
        self.clear_button.pack(side="left", padx=(8, 0))

        self.progress = ttk.Progressbar(frame, mode="determinate")
        self.progress.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(0, 6))
        self.status_var = tk.StringVar(value="Bereit. Suchtext und Ordner auswählen.")
        ttk.Label(frame, textvariable=self.status_var).grid(row=6, column=0, columnspan=3, sticky="w", pady=(0, 4))
        self.summary_var = tk.StringVar(value="Noch keine Suche abgeschlossen.")
        ttk.Label(frame, textvariable=self.summary_var).grid(row=7, column=0, columnspan=3, sticky="w", pady=(0, 8))

        ttk.Label(frame, text="Gefundene Dateien (vollständiger Pfad):").grid(row=8, column=0, columnspan=3, sticky="w", pady=(4, 4))
        results_frame = ttk.Frame(frame)
        results_frame.grid(row=9, column=0, columnspan=3, sticky="nsew")
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(results_frame, columns=("path",), show="headings")
        self.tree.heading("path", text="Dateipfad")
        self.tree.column("path", width=80, minwidth=80, anchor="w", stretch=True)
        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll = ttk.Scrollbar(results_frame, orient="vertical", command=self.tree.yview)
        yscroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=yscroll.set)
        xscroll = ttk.Scrollbar(results_frame, orient="horizontal", command=self.tree.xview)
        xscroll.grid(row=1, column=0, sticky="ew")
        self.tree.configure(xscrollcommand=xscroll.set)
        self.tree.after_idle(self._fit_path_column)
        # Doppelklick oder die Schaltfläche öffnen die TB2-Datei mit dem in Windows verknüpften Programm.
        self.tree.bind("<Double-1>", self.open_result_file)
        self.tree.bind("<<TreeviewSelect>>", self._update_open_button_state)

        footer = ttk.Frame(frame)
        footer.grid(row=10, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        ttk.Button(footer, text="Programm beenden", command=self.request_exit).pack(side="right")
        ttk.Button(footer, text="Info", command=self.show_info).pack(side="right", padx=(0, 8))

        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(9, weight=1)
        self.term_entry.focus_set()

    def show_info(self):
        """Show application details and the former footer help text."""
        dialog = tk.Toplevel(self)
        dialog.title("Info – TB2-Textfinder")
        center_window(dialog, 650, 380, parent=self)
        dialog.minsize(480, 300)
        dialog.transient(self)
        body = ttk.Frame(dialog, padding=18)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text=f"{APP_TITLE} – Version {APP_VERSION}",
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
                                  if not os.path.isjunction(os.path.join(directory, name))]
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
                    from tb2_jpeg_fast import contains_term_fast
                    data = mask_resource_paths(path.read_bytes())
                    # Zweistufige Ganzwortsuche: Nur Kandidaten mit einem
                    # Teilworttreffer benötigen die teure Wortgrenzenprüfung.
                    # JPEG-Bereiche werden in beiden Stufen identisch behandelt.
                    candidate = contains_term_fast(data, term, case_sensitive)
                    if whole_word and candidate:
                        from tb2_jpeg_fast import jpeg_ranges
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
                    for path in found:
                        self.tree.insert("", "end", values=(path,))
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
        # Treeview dehnt die Spalte selbst auf den verfügbaren Platz aus.
        # Die Widgetbreite darf nicht als Spaltenbreite verwendet werden:
        # Rahmen und Innenabstände würden sonst unnötiges Scrollen auslösen.
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
        )
        if not destination:
            return
        try:
            Path(destination).write_text("\n".join(self.result_paths) + "\n", encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("Speichern fehlgeschlagen", str(exc))
            return
        self.status_var.set(f"Pfadliste gespeichert: {destination}")

    def clear_results(self):
        if self.scanning:
            return
        self.result_paths = []
        self.access_issues = []
        self.issues_button.pack_forget()
        self.clear_button.configure(state="disabled")
        self.clear_button.configure(state="disabled")
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.copy_button.configure(state="disabled")
        self.open_button.configure(state="disabled")
        self.save_button.configure(state="disabled")
        self._fit_path_column([])
        self.status_var.set("Ergebnisliste geleert.")
        self.summary_var.set("Noch keine Suche abgeschlossen.")


if __name__ == "__main__":
    App().mainloop()