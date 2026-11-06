#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TB2-Negativtester – erkennt Dateien ohne bekannte TB2-Textstruktur.

Ein Treffer bedeutet ausschließlich, dass mindestens drei aufeinanderfolgende
Zeichen zu einem der bislang untersuchten Glyphenprofile passen. Ein Nichttreffer
beweist nicht, dass eine Datei keinen Text enthält.
"""
from __future__ import annotations

import os
import queue
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from TB2_Textfinder import PROFILES, _find_all

APP_TITLE = "TB2-Negativtester"
APP_VERSION = "0.1 – Testversion"
MIN_CHARACTERS = 3


def _printable_codes() -> set[int]:
    """Bytewerte, die in den getesteten Ein-Byte-Zeichensätzen druckbar sind."""
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
    """Return True if a known marker/stride profile contains N valid records."""
    if not data or minimum < 1:
        return False

    for _name, marker, strides in PROFILES:
        marker_length = len(marker)
        for stride in strides:
            # The marker follows the character byte in every observed record.
            for marker_pos in _find_all(data, marker):
                first_char_pos = marker_pos - 1
                if first_char_pos < 0 or data[first_char_pos] not in PRINTABLE_CODES:
                    continue

                matched = True
                for index in range(1, minimum):
                    char_pos = first_char_pos + index * stride
                    next_marker_pos = char_pos + 1
                    if (char_pos >= len(data)
                            or data[char_pos] not in PRINTABLE_CODES
                            or data[next_marker_pos:next_marker_pos + marker_length] != marker):
                        matched = False
                        break
                if matched:
                    return True
    return False


def inspect_file(path: Path) -> tuple[str, str]:
    """Return (category, detail): recognized, unknown, empty, or error."""
    try:
        data = path.read_bytes()
    except OSError as exc:
        return "Fehler", str(exc)
    if not data:
        return "Leer", "Datei enthält 0 Bytes"
    if has_known_glyph_pattern(data):
        return "Erkannt", "Bekanntes Muster (mindestens 3 Zeichen)"
    return "Unbekannt", "Kein bekanntes Textmuster erkannt"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_TITLE} – {APP_VERSION}")
        self.geometry("1000x650")
        self.minsize(760, 460)
        self.events: queue.Queue = queue.Queue()
        self.scanning = False
        self.rows: list[tuple[str, str, str]] = []
        self._build_ui()
        self.after(100, self._poll_events)

    def _build_ui(self):
        frame = ttk.Frame(self, padding=14)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Zu prüfender Ordner:").grid(row=0, column=0, sticky="w")
        self.folder_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.folder_var).grid(
            row=0, column=1, sticky="ew", padx=10
        )
        ttk.Button(frame, text="Ordner wählen …", command=self.choose_folder).grid(
            row=0, column=2
        )

        self.recursive_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frame, text="Unterordner einbeziehen", variable=self.recursive_var
        ).grid(row=1, column=1, sticky="w", pady=(9, 2))

        actions = ttk.Frame(frame)
        actions.grid(row=2, column=0, columnspan=3, sticky="w", pady=(12, 10))
        self.scan_button = ttk.Button(actions, text="Ordner prüfen", command=self.start_scan)
        self.scan_button.pack(side="left")
        self.open_button = ttk.Button(
            actions, text="Datei öffnen", command=self.open_selected, state="disabled"
        )
        self.open_button.pack(side="left", padx=(8, 0))
        self.copy_button = ttk.Button(
            actions, text="Pfade kopieren", command=self.copy_paths, state="disabled"
        )
        self.copy_button.pack(side="left", padx=(8, 0))
        self.save_button = ttk.Button(
            actions, text="Liste als TXT speichern …", command=self.save_report,
            state="disabled"
        )
        self.save_button.pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Leeren", command=self.clear).pack(side="left", padx=(8, 0))

        self.progress = ttk.Progressbar(frame, mode="determinate")
        self.progress.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 7))
        self.status_var = tk.StringVar(value="Bereit. Ordner auswählen und Prüfung starten.")
        ttk.Label(frame, textvariable=self.status_var).grid(
            row=4, column=0, columnspan=3, sticky="w", pady=(0, 8)
        )

        ttk.Label(
            frame, text="Auffällige Dateien (unbekannt, leer oder nicht lesbar):"
        ).grid(row=5, column=0, columnspan=3, sticky="w", pady=(3, 4))

        self.tree = ttk.Treeview(frame, columns=("category", "path", "detail"), show="headings")
        self.tree.heading("category", text="Status")
        self.tree.heading("path", text="Vollständiger Dateipfad")
        self.tree.heading("detail", text="Hinweis")
        self.tree.column("category", width=105, stretch=False)
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

        note = (
            "Prüft .TB2-Dateien anhand der bislang bekannten Marker und Datensatzabstände "
            "(80 bzw. 106 Byte). Als erkannt gelten mindestens drei aufeinanderfolgende "
            "druckbare Zeichen mit passender Struktur. Die Liste zeigt nur auffällige Dateien. "
            "„Kein bekanntes Textmuster erkannt“ bedeutet ausdrücklich nicht, dass die Datei "
            "keinen Text enthält – möglicherweise verwendet sie ein noch unbekanntes Format."
        )
        ttk.Label(frame, text=note, wraplength=950, foreground="#555555").grid(
            row=8, column=0, columnspan=3, sticky="w", pady=(10, 0)
        )
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(6, weight=1)

    def choose_folder(self):
        folder = filedialog.askdirectory(title="Ordner mit TB2-Dateien auswählen")
        if folder:
            self.folder_var.set(folder)

    def start_scan(self):
        folder_text = self.folder_var.get().strip()
        if not folder_text or not Path(folder_text).is_dir():
            messagebox.showwarning("Ordner fehlt", "Bitte einen gültigen Ordner auswählen.")
            return
        if self.scanning:
            return

        root = Path(folder_text)
        candidates = root.rglob("*") if self.recursive_var.get() else root.glob("*")
        files = [p for p in candidates if p.is_file() and p.suffix.lower() == ".tb2"]
        if not files:
            messagebox.showinfo("Keine TB2-Dateien", "Im Ordner wurden keine .TB2-Dateien gefunden.")
            return

        self.scanning = True
        self.rows = []
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.scan_button.configure(state="disabled")
        self.progress.configure(maximum=len(files), value=0)
        self.status_var.set(f"Prüfe {len(files)} TB2-Datei(en) …")
        threading.Thread(target=self._worker, args=(files,), daemon=True).start()

    def _worker(self, files: list[Path]):
        flagged: list[tuple[str, str, str]] = []
        recognized = errors = empty = 0
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
            self.events.put(("progress", index, len(files), path.name))
        self.events.put(("finished", flagged, len(files), recognized, empty, errors))

    def _poll_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                if event[0] == "progress":
                    _, current, total, name = event
                    self.progress.configure(value=current)
                    self.status_var.set(f"Datei {current}/{total}: {name}")
                elif event[0] == "finished":
                    _, flagged, total, recognized, empty, errors = event
                    self.rows = flagged
                    for category, path, detail in flagged:
                        self.tree.insert("", "end", values=(category, path, detail))
                    self.scanning = False
                    self.scan_button.configure(state="normal")
                    state = "normal" if flagged else "disabled"
                    self.copy_button.configure(state=state)
                    self.save_button.configure(state=state)
                    self.open_button.configure(state="disabled")
                    unknown = sum(1 for row in flagged if row[0] == "Unbekannt")
                    self.status_var.set(
                        f"Fertig: {total} Datei(en) geprüft | {recognized} erkannt | "
                        f"{unknown} unbekannt | {empty} leer | {errors} Lesefehler."
                    )
        except queue.Empty:
            pass
        self.after(100, self._poll_events)

    def update_buttons(self, _event=None):
        state = "normal" if len(self.tree.selection()) == 1 else "disabled"
        self.open_button.configure(state=state)

    def selected_path(self) -> str | None:
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

    def open_path(self, path: str):
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
        paths = [row[1] for row in self.rows]
        if paths:
            self.clipboard_clear()
            self.clipboard_append("\n".join(paths))
            self.status_var.set(f"{len(paths)} Pfad/Pfade kopiert.")

    def save_report(self):
        if not self.rows:
            return
        destination = filedialog.asksaveasfilename(
            title="Prüfbericht speichern", defaultextension=".txt",
            filetypes=[("Textdatei", "*.txt"), ("Alle Dateien", "*.*")],
            initialfile="TB2_Negativtester_Bericht.txt"
        )
        if not destination:
            return
        lines = [
            "TB2-Negativtester – Prüfbericht",
            "Hinweis: Ein Nichttreffer beweist nicht, dass die Datei keinen Text enthält.",
            ""
        ]
        lines.extend(f"{category}\t{path}\t{detail}" for category, path, detail in self.rows)
        try:
            Path(destination).write_text("\n".join(lines) + "\n", encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("Speichern fehlgeschlagen", str(exc))
            return
        self.status_var.set(f"Bericht gespeichert: {destination}")

    def clear(self):
        self.rows = []
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.copy_button.configure(state="disabled")
        self.open_button.configure(state="disabled")
        self.save_button.configure(state="disabled")
        self.status_var.set("Ergebnisliste geleert.")


if __name__ == "__main__":
    App().mainloop()
