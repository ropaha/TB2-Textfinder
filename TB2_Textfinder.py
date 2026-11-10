#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TB2-Textfinder 1.8.2

Durchsucht .TB2-Dateien nach lesbarem Text und bislang beobachteten
SignumNext-Glyphenprofilen mehrerer Formatgenerationen. Treffer werden
als vollständige Dateipfade ausgegeben; interne Offsets bleiben verborgen.
"""
from __future__ import annotations

import os
import queue
import threading
from time import perf_counter
from tb2_resource_paths import mask_resource_paths
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_TITLE = "TB2-Textfinder"
APP_VERSION = "1.8.3-dev"
MIT_LICENSE = "MIT License\n\nCopyright (c) 2026 Roga Hagen (roga@hagen.me)\n\nPermission is hereby granted, free of charge, to any person obtaining a copy\nof this software and associated documentation files (the \"Software\"), to deal\nin the Software without restriction, including without limitation the rights\nto use, copy, modify, merge, publish, distribute, sublicense, and/or sell\ncopies of the Software, and to permit persons to whom the Software is\nfurnished to do so, subject to the following conditions:\n\nThe above copyright notice and this permission notice shall be included in all\ncopies or substantial portions of the Software.\n\nTHE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\nIMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\nFITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\nAUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\nLIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\nOUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE\nSOFTWARE.\n"

INFO_TEXT = (
    "Schnell überspringt JPEG-Daten und kann Treffer übersehen; Vollständig entspricht der bisherigen Suche. "
    "Datei in der Trefferliste markieren und auf 'Datei öffnen' klicken – "
    "oder den Treffer doppelt anklicken. Die TB2-Datei wird mit dem in Windows "
    "verknüpften Programm. Suche in Klartext sowie in untersuchten TB2-Glyphenmustern mehrerer Generationen "
    "(Datensatzabstände 80, 98, 106 und 587 Byte, mit unterschiedlichen Markern). Umlaute und weitere Ein-Byte-Zeichen werden "
    "berücksichtigt. Die Groß-/Kleinschreibung wird standardmäßig ignoriert – auch bei "
    "Umlauten. Die Dateiformate werden weiter untersucht; ein Nichttreffer ist daher "
    "noch kein Beweis, dass der Text fehlt."
)

PROFILES = (
    # Neue und mittlere Generation: Zeichen + Marker, Abstand 106 Bytes.
    ("SignumNext-Profil A", b"\x81\x00\x00", (0x6A,)),
    ("SignumNext-Profil B", b"\x81\x67\x66\x66\x66\x66\x81", (0x6A,)),
    # Ältere Generation (z. B. Datei 9500036.TB2, Jahrgang 1995):
    # gleicher Zeichenmarker, aber nur 80 Bytes Abstand.
    ("Signum-Altformat", b"\x81\x00\x00", (0x50,)),
    # Sehr frühe Generation (z. B. 8900001.TB2):
    # eigener Marker direkt hinter jedem Zeichen; ebenfalls 80 Bytes Abstand.
    ("Signum-Frühformat", b"\x81\x7C\xE9\xE4\x58\x09", (0x50,)),
    # 1990–1993: 98-Byte-Datensaetze, variabler 6-Byte-Vorspann
    # zwischen Zeichen und festem Marker 81 00 00.
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



def _variable_marker_record(data: bytes, pos: int) -> bool:
    """Ältere 80-Byte-Glyphen: variable 5-Byte-Felder nach 0x81.

    Beobachtet bei 9005016.TB2. Das Folgesteuerbyte an +7 ist
    0x80 oder 0x81. Diese Struktur vermeidet blindes Stride-Matching.
    """
    return (pos >= 0 and pos + 8 <= len(data)
            and data[pos + 1] == 0x81
            and data[pos + 7] in (0x80, 0x81))


def _early_80_record(data: bytes, pos: int) -> bool:
    """Frühes 80-Byte-Profil mit 0x80 direkt nach dem Zeichen.

    Beobachtet in 9518311I.TB2 (Kl.Gladebrügge). Die 5 variablen
    Steuerbytes werden nicht als feste Signatur interpretiert.
    """
    return (0 <= pos and pos + 8 <= len(data)
            and data[pos + 1] == 0x80
            and data[pos + 7] in (0x80, 0x81))


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


def has_early_80_pattern(data: bytes, minimum: int = 3) -> bool:
    minimum = max(3, minimum)
    for marker_pos in _find_all(data, b"\x80"):
        start = marker_pos - 1
        if start < 0 or start + (minimum - 1) * 80 + 8 > len(data):
            continue
        if all(_early_80_record(data, start + i * 80)
               and (32 <= data[start + i * 80] <= 126
                    or data[start + i * 80] >= 0x80)
               for i in range(minimum)):
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


def has_variable_80_pattern(data: bytes, minimum: int = 3) -> bool:
    """Mindestens drei plausible Datensätze mit variablem Marker."""
    if minimum < 3:
        minimum = 3
    for marker_pos in _find_all(data, b"\x81"):
        start = marker_pos - 1
        if start < 0:
            continue
        if all(_variable_marker_record(data, start + i * 80)
               and (32 <= data[start + i * 80] <= 126
                    or data[start + i * 80] >= 0x80)
               for i in range(minimum)
               if start + i * 80 < len(data)):
            if start + (minimum - 1) * 80 + 8 <= len(data):
                return True
    return False

def _wide_587_record(data: bytes, pos: int) -> bool:
    """587-Byte-Glyphen mit beobachteten Steuerbytes 7E/7F/80/81/84."""
    return (0 <= pos and pos + 8 <= len(data)
            and data[pos + 1] in (0x7E, 0x7F, 0x80, 0x81, 0x84)
            and data[pos + 7] in (0x80, 0x81))


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


def has_wide_587_pattern(data: bytes, minimum: int = 3) -> bool:
    """Mindestens drei aufeinanderfolgende plausible 587-Byte-Zeichen."""
    minimum = max(3, minimum)
    for marker in (b"\x7e", b"\x7f", b"\x80", b"\x81", b"\x84"):
        for marker_pos in _find_all(data, marker):
            start = marker_pos - 1
            if start < 0 or start + (minimum - 1) * 587 + 8 > len(data):
                continue
            if all(_wide_587_record(data, start + i * 587)
                   and (32 <= data[start + i * 587] <= 126
                        or data[start + i * 587] >= 0x80)
                   for i in range(minimum)):
                return True
    return False




def _early_82_record(data: bytes, pos: int) -> bool:
    """80-Byte-Zeichendatensatz mit 0x82 nach dem Zeichen.

    Referenz: 9600246.TB2 (HANDELSHAUS). Der Vorspann an +2..+6
    kann variieren; +7 ist bei diesem Datensatz 0x80 oder 0x81.
    """
    return (0 <= pos and pos + 8 <= len(data)
            and data[pos + 1] == 0x82
            and data[pos + 7] in (0x80, 0x81))


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


def has_early_82_pattern(data: bytes, minimum: int = 3) -> bool:
    minimum = max(3, minimum)
    for marker_pos in _find_all(data, b"\x82"):
        start = marker_pos - 1
        if start < 0 or start + (minimum - 1) * 80 + 8 > len(data):
            continue
        if all(_early_82_record(data, start + i * 80)
               and (32 <= data[start + i * 80] <= 126
                    or data[start + i * 80] >= 0x80)
               for i in range(minimum)):
            return True
    return False



def _variable_98_record(data: bytes, pos: int) -> bool:
    """98-Byte-Zeichen: variables Steuerfeld und 0x80/0x81 an Position +7.

    Referenz 2006 18 178d.TB2 (1923 INGEBORG 2006).
    Erfordert 0x80/0x81 an +1 und 0x80/0x81 an +7; kein blindes Stride-Matching.
    """
    return (0 <= pos and pos + 8 <= len(data)
            and data[pos + 1] in (0x80, 0x81)
            and data[pos + 7] in (0x80, 0x81))


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


def has_variable_98_pattern(data: bytes, minimum: int = 3) -> bool:
    minimum = max(3, minimum)
    for marker in (b"\x80", b"\x81"):
        for marker_pos in _find_all(data, marker):
            start = marker_pos - 1
            if start < 0 or start + (minimum - 1) * 98 + 8 > len(data):
                continue
            if all(_variable_98_record(data, start + i * 98)
                   and (32 <= data[start + i * 98] <= 126
                        or data[start + i * 98] >= 0x80)
                   for i in range(minimum)):
                return True
    return False

def _variable_106_record(data: bytes, pos: int) -> bool:
    """106-Byte-Glyphen mit variablen Steuerdaten.

    Referenzen: 2018-00-149.TB2 (Fuchs) und 2020-01-012.TB2
    (Oma, Felicitas). Das Steuerbyte an +1 darf 0x81 oder 0x82
    sein; die 5 folgenden Bytes sind variabel. Die beobachtete
    Abschlussstruktur +7..+9 bleibt verpflichtend.
    """
    return (0 <= pos and pos + 10 <= len(data)
            and data[pos + 1] in (0x81, 0x82)
            and data[pos + 7:pos + 10] == b"\x81\x00\x00")


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


def has_variable_106_pattern(data: bytes, minimum: int = 3) -> bool:
    minimum = max(3, minimum)
    for marker in (b"\x81", b"\x82"):
        for marker_pos in _find_all(data, marker):
            start = marker_pos - 1
            if start < 0 or start + (minimum - 1) * 106 + 10 > len(data):
                continue
            if all(_variable_106_record(data, start + i * 106)
                   and (32 <= data[start + i * 106] <= 126
                        or data[start + i * 106] >= 0x80)
                   for i in range(minimum)):
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


def scan_file(path: Path, term: str, case_sensitive: bool) -> tuple[bool, str | None]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        return False, str(exc)
    return contains_term(mask_resource_paths(data), term, case_sensitive), None


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_TITLE} – {APP_VERSION}")
        self.geometry("940x600")
        self.minsize(720, 420)
        self.events: queue.Queue = queue.Queue()
        self.scanning = False
        self.result_paths: list[str] = []
        self._build_ui()
        self.after(100, self._poll_events)

    def _build_ui(self):
        frame = ttk.Frame(self, padding=14)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Gesuchter Text:").grid(row=0, column=0, sticky="w")
        self.term_var = tk.StringVar()
        self.term_entry = ttk.Entry(frame, textvariable=self.term_var, width=38)
        self.term_entry.grid(row=0, column=1, sticky="ew", padx=(10, 10))

        ttk.Label(frame, text="Ordner:").grid(row=1, column=0, sticky="w", pady=(12, 0))
        self.folder_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.folder_var).grid(
            row=1, column=1, sticky="ew", padx=(10, 10), pady=(12, 0)
        )
        ttk.Button(frame, text="Ordner wählen …", command=self.choose_folder).grid(
            row=1, column=2, pady=(12, 0)
        )

        options = ttk.Frame(frame)
        options.grid(row=2, column=1, columnspan=2, sticky="w", pady=(10, 2))
        self.recursive_var = tk.BooleanVar(value=True)
        self.case_var = tk.BooleanVar(value=False)
        self.search_mode_var = tk.StringVar(value="fast")
        ttk.Checkbutton(options, text="Unterordner einbeziehen", variable=self.recursive_var).pack(side="left", padx=(0, 20))
        ttk.Checkbutton(options, text="Groß-/Kleinschreibung beachten", variable=self.case_var).pack(side="left")

        mode_options = ttk.Frame(frame)
        mode_options.grid(row=3, column=1, columnspan=2, sticky="w", pady=(4, 2))
        ttk.Label(mode_options, text="Suchmodus:").pack(side="left", padx=(0, 10))
        ttk.Radiobutton(mode_options, text="Vollständig (alle Bytes)", variable=self.search_mode_var,
                        value="full").pack(side="left", padx=(0, 14))
        ttk.Radiobutton(mode_options, text="Schnell (JPEG überspringen)",
                        variable=self.search_mode_var, value="fast").pack(side="left")

        actions = ttk.Frame(frame)
        actions.grid(row=4, column=0, columnspan=3, sticky="w", pady=(12, 10))
        self.search_button = ttk.Button(actions, text="Suchen", command=self.start_scan)
        self.search_button.pack(side="left")
        self.open_button = ttk.Button(
            actions, text="Datei öffnen", command=self.open_selected_file, state="disabled"
        )
        self.open_button.pack(side="left", padx=(8, 0))
        self.copy_button = ttk.Button(actions, text="Pfade kopieren", command=self.copy_paths, state="disabled")
        self.copy_button.pack(side="left", padx=(8, 0))
        self.save_button = ttk.Button(actions, text="Pfade als TXT speichern …", command=self.save_paths, state="disabled")
        self.save_button.pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Leeren", command=self.clear_results).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Info", command=self.show_info).pack(side="left", padx=(8, 0))

        self.progress = ttk.Progressbar(frame, mode="determinate")
        self.progress.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(0, 6))
        self.status_var = tk.StringVar(value="Bereit. Suchtext und Ordner auswählen.")
        ttk.Label(frame, textvariable=self.status_var).grid(row=6, column=0, columnspan=3, sticky="w", pady=(0, 8))

        ttk.Label(frame, text="Gefundene Dateien (vollständiger Pfad):").grid(row=7, column=0, columnspan=3, sticky="w", pady=(4, 4))
        self.tree = ttk.Treeview(frame, columns=("path",), show="headings")
        self.tree.heading("path", text="Dateipfad")
        self.tree.column("path", width=880, anchor="w")
        self.tree.grid(row=8, column=0, columnspan=2, sticky="nsew")
        yscroll = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        yscroll.grid(row=8, column=2, sticky="ns")
        self.tree.configure(yscrollcommand=yscroll.set)
        xscroll = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
        xscroll.grid(row=9, column=0, columnspan=2, sticky="ew")
        self.tree.configure(xscrollcommand=xscroll.set)
        # Doppelklick oder die Schaltfläche öffnen die TB2-Datei mit dem in Windows verknüpften Programm.
        self.tree.bind("<Double-1>", self.open_result_file)
        self.tree.bind("<<TreeviewSelect>>", self._update_open_button_state)

        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(8, weight=1)
        self.term_entry.focus_set()

    def show_info(self):
        """Show application details and the former footer help text."""
        dialog = tk.Toplevel(self)
        dialog.title("Info – TB2-Textfinder")
        dialog.geometry("650x380")
        dialog.minsize(420, 280)
        dialog.transient(self)
        body = ttk.Frame(dialog, padding=18)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text=f"{APP_TITLE} – Version {APP_VERSION}",
                  font=("TkDefaultFont", 13, "bold")).pack(anchor="w", pady=(0, 12))
        help_frame = ttk.Frame(body)
        help_frame.pack(fill="both", expand=True)
        help_text = tk.Text(help_frame, wrap="word", height=9, relief="flat",
                            background=dialog.cget("background"), padx=2, pady=2)
        help_text.insert("1.0", INFO_TEXT)
        help_text.configure(state="disabled")
        help_text.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(help_frame, orient="vertical", command=help_text.yview)
        scrollbar.pack(side="right", fill="y")
        help_text.configure(yscrollcommand=scrollbar.set)
        buttons = ttk.Frame(body)
        buttons.pack(fill="x", pady=(14, 0))
        ttk.Button(buttons, text="MIT-Lizenz anzeigen",
                   command=lambda: self.show_license(dialog)).pack(side="left")
        ttk.Button(buttons, text="Schließen", command=dialog.destroy).pack(side="right")

    def show_license(self, parent):
        """Display the complete license bundled with this program."""
        dialog = tk.Toplevel(parent)
        dialog.title("MIT-Lizenz – TB2-Textfinder")
        dialog.geometry("720x450")
        dialog.minsize(450, 300)
        dialog.transient(parent)
        body = ttk.Frame(dialog, padding=14)
        body.pack(fill="both", expand=True)
        text_frame = ttk.Frame(body)
        text_frame.pack(fill="both", expand=True)
        license_text = tk.Text(text_frame, wrap="word", font=("TkFixedFont", 10))
        license_text.insert("1.0", MIT_LICENSE)
        license_text.configure(state="disabled")
        license_text.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=license_text.yview)
        scrollbar.pack(side="right", fill="y")
        license_text.configure(yscrollcommand=scrollbar.set)
        ttk.Button(body, text="Schließen", command=dialog.destroy).pack(anchor="e", pady=(10, 0))

    def choose_folder(self):
        folder = filedialog.askdirectory(title="Ordner mit TB2-/TBL-Dateien auswählen")
        if folder:
            self.folder_var.set(folder)

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

        root = Path(folder_text)
        candidates = root.rglob("*") if self.recursive_var.get() else root.glob("*")
        files = [p for p in candidates if p.is_file() and p.suffix.lower() in {".tb2", ".tbl"}]
        if not files:
            messagebox.showinfo("Keine TB2-/TBL-Dateien", "Im ausgewählten Ordner wurden keine .TB2- oder .TBL-Dateien gefunden.")
            return

        self.scanning = True
        self.result_paths = []
        self.search_button.configure(state="disabled")
        self.copy_button.configure(state="disabled")
        self.open_button.configure(state="disabled")
        self.save_button.configure(state="disabled")
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.progress.configure(maximum=len(files), value=0)
        self.status_var.set(f"Untersuche {len(files)} TB2-/TBL-Datei(en) …")
        threading.Thread(
            target=self._scan_worker,
            args=(files, term, self.case_var.get(), self.search_mode_var.get()),
            daemon=True,
        ).start()

    def _scan_worker(self, files: list[Path], term: str, case_sensitive: bool, mode: str):
        found: list[str] = []
        errors = 0
        started = perf_counter()
        for index, path in enumerate(files, start=1):
            if mode == "fast":
                try:
                    from tb2_jpeg_fast import contains_term_fast
                    hit = contains_term_fast(mask_resource_paths(path.read_bytes()), term, case_sensitive)
                    error = None
                except (OSError, ValueError, MemoryError) as exc:
                    hit, error = False, str(exc)
            else:
                hit, error = scan_file(path, term, case_sensitive)
            if hit:
                found.append(str(path.resolve()))
            if error:
                errors += 1
            self.events.put(("progress", index, len(files), path.name))
        self.events.put(("finished", found, len(files), errors, mode, perf_counter() - started))

    def _poll_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                if event[0] == "progress":
                    _, current, total, filename = event
                    self.progress.configure(value=current)
                    self.status_var.set(f"Datei {current}/{total}: {filename}")
                elif event[0] == "finished":
                    _, found, total, errors, mode, seconds = event
                    self.result_paths = found
                    for path in found:
                        self.tree.insert("", "end", values=(path,))
                    self.scanning = False
                    self.search_button.configure(state="normal")
                    state = "normal" if found else "disabled"
                    self.copy_button.configure(state=state)
                    self.save_button.configure(state=state)
                    # Die Datei-Öffnen-Schaltfläche wird erst nach Auswahl eines Treffers aktiviert.
                    self.open_button.configure(state="disabled")
                    msg = f"Fertig ({'Schnell' if mode == 'fast' else 'Vollständig'}): {len(found)} Treffer in {total} Datei(en) – {seconds:.2f} s."
                    if errors:
                        msg += f" {errors} Datei(en) konnten nicht gelesen werden."
                    self.status_var.set(msg)
        except queue.Empty:
            pass
        self.after(100, self._poll_events)

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
        self.status_var.set(f"{len(self.result_paths)} Pfad/Pfade in die Zwischenablage kopiert.")

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
        self.result_paths = []
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.copy_button.configure(state="disabled")
        self.open_button.configure(state="disabled")
        self.save_button.configure(state="disabled")
        self.status_var.set("Ergebnisliste geleert.")


if __name__ == "__main__":
    App().mainloop()