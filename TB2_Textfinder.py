#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TB2-Textfinder 0.7

Durchsucht .TB2-Dateien nach lesbarem Text und bislang beobachteten
SignumNext-Glyphenprofilen mehrerer Formatgenerationen. Treffer werden
als vollständige Dateipfade ausgegeben; interne Offsets bleiben verborgen.
"""
from __future__ import annotations

import os
import queue
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_TITLE = "TB2-Textfinder"
APP_VERSION = "0.7 – Testversion"
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
    return codes


def _matches_glyph_profile(data: bytes, term: str, marker: bytes,
                           stride: int, case_sensitive: bool) -> bool:
    """Check one character per record with the selected record spacing."""
    if not term:
        return False

    char_codes = [_glyph_char_codes(ch, case_sensitive) for ch in term]
    if any(not codes for codes in char_codes):
        return False

    # Locate possible first records, then verify each character's encoded byte.
    for first_code in char_codes[0]:
        lead = bytes([first_code]) + marker
        for start in _find_all(data, lead):
            matched = True
            for index, allowed_codes in enumerate(char_codes):
                pos = start + index * stride
                if pos + 1 + len(marker) > len(data):
                    matched = False
                    break
                if data[pos] not in allowed_codes:
                    matched = False
                    break
                if data[pos + 1:pos + 1 + len(marker)] != marker:
                    matched = False
                    break
            if matched:
                return True
    return False


def contains_term(data: bytes, term: str, case_sensitive: bool = False) -> bool:
    if any(data.find(needle) >= 0 for needle in _plain_needles(term, case_sensitive)):
        return True
    for _profile_name, marker, strides in PROFILES:
        for stride in strides:
            if _matches_glyph_profile(data, term, marker, stride, case_sensitive):
                return True
    return False


def scan_file(path: Path, term: str, case_sensitive: bool) -> tuple[bool, str | None]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        return False, str(exc)
    return contains_term(data, term, case_sensitive), None


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
        ttk.Checkbutton(options, text="Unterordner einbeziehen", variable=self.recursive_var).pack(side="left", padx=(0, 20))
        ttk.Checkbutton(options, text="Groß-/Kleinschreibung beachten", variable=self.case_var).pack(side="left")

        actions = ttk.Frame(frame)
        actions.grid(row=3, column=0, columnspan=3, sticky="w", pady=(12, 10))
        self.search_button = ttk.Button(actions, text="Suchen", command=self.start_scan)
        self.search_button.pack(side="left")
        self.copy_button = ttk.Button(actions, text="Pfade kopieren", command=self.copy_paths, state="disabled")
        self.copy_button.pack(side="left", padx=(8, 0))
        self.open_button = ttk.Button(
            actions, text="Datei öffnen", command=self.open_selected_file, state="disabled"
        )
        self.open_button.pack(side="left", padx=(8, 0))
        self.save_button = ttk.Button(actions, text="Pfade als TXT speichern …", command=self.save_paths, state="disabled")
        self.save_button.pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Leeren", command=self.clear_results).pack(side="left", padx=(8, 0))

        self.progress = ttk.Progressbar(frame, mode="determinate")
        self.progress.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(0, 6))
        self.status_var = tk.StringVar(value="Bereit. Suchtext und Ordner auswählen.")
        ttk.Label(frame, textvariable=self.status_var).grid(row=5, column=0, columnspan=3, sticky="w", pady=(0, 8))

        ttk.Label(frame, text="Gefundene Dateien (vollständiger Pfad):").grid(row=6, column=0, columnspan=3, sticky="w", pady=(4, 4))
        self.tree = ttk.Treeview(frame, columns=("path",), show="headings")
        self.tree.heading("path", text="Dateipfad")
        self.tree.column("path", width=880, anchor="w")
        self.tree.grid(row=7, column=0, columnspan=2, sticky="nsew")
        yscroll = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        yscroll.grid(row=7, column=2, sticky="ns")
        self.tree.configure(yscrollcommand=yscroll.set)
        xscroll = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
        xscroll.grid(row=8, column=0, columnspan=2, sticky="ew")
        self.tree.configure(xscrollcommand=xscroll.set)
        # Doppelklick oder die Schaltfläche öffnen die TB2-Datei mit dem in Windows verknüpften Programm.
        self.tree.bind("<Double-1>", self.open_result_file)
        self.tree.bind("<<TreeviewSelect>>", self._update_open_button_state)

        note = ("Datei in der Trefferliste markieren und auf 'Datei öffnen' klicken – "
                "oder den Treffer doppelt anklicken. Die TB2-Datei wird mit dem in Windows "
                "verknüpften Programm geöffnet. Suche in Klartext sowie in untersuchten TB2-Glyphenmustern mehrerer Generationen "
                "(Datensatzabstände 80 und 106 Byte, mit unterschiedlichen Markern). Umlaute und weitere Ein-Byte-Zeichen werden "
                "berücksichtigt. Die Groß-/Kleinschreibung wird standardmäßig ignoriert – auch bei "
                "Umlauten. Die Dateiformate werden weiter untersucht; ein Nichttreffer ist daher "
                "noch kein Beweis, dass der Text fehlt.")
        ttk.Label(frame, text=note, wraplength=900, foreground="#555555").grid(
            row=9, column=0, columnspan=3, sticky="w", pady=(10, 0)
        )
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(7, weight=1)
        self.term_entry.focus_set()

    def choose_folder(self):
        folder = filedialog.askdirectory(title="Ordner mit TB2-Dateien auswählen")
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
        files = [p for p in candidates if p.is_file() and p.suffix.lower() == ".tb2"]
        if not files:
            messagebox.showinfo("Keine TB2-Dateien", "Im ausgewählten Ordner wurden keine .TB2-Dateien gefunden.")
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
        self.status_var.set(f"Untersuche {len(files)} TB2-Datei(en) …")
        threading.Thread(
            target=self._scan_worker,
            args=(files, term, self.case_var.get()),
            daemon=True,
        ).start()

    def _scan_worker(self, files: list[Path], term: str, case_sensitive: bool):
        found: list[str] = []
        errors = 0
        for index, path in enumerate(files, start=1):
            hit, error = scan_file(path, term, case_sensitive)
            if hit:
                found.append(str(path.resolve()))
            if error:
                errors += 1
            self.events.put(("progress", index, len(files), path.name))
        self.events.put(("finished", found, len(files), errors))

    def _poll_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                if event[0] == "progress":
                    _, current, total, filename = event
                    self.progress.configure(value=current)
                    self.status_var.set(f"Datei {current}/{total}: {filename}")
                elif event[0] == "finished":
                    _, found, total, errors = event
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
                    msg = f"Fertig: {len(found)} Treffer in {total} Datei(en)."
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
