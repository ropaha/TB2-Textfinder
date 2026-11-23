#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Experimenteller TB2-Textcounter: zunächst nur bekannte 106-Byte-Textzeilen."""
from __future__ import annotations
import argparse
from collections import Counter
from pathlib import Path
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

FONT_PATTERN = re.compile(rb"Signum Standard\\([A-Za-z0-9_. -]{1,64})")
STRIDE = 106
FIRST_CHAR_OFFSET = 343
SPACE_CODE = 0xFA

def valid_record(data: bytes, pos: int) -> bool:
    return (0 <= pos and pos + 8 <= len(data) and
            (data[pos + 1:pos + 4] == b"\x81\x00\x00" or
             (data[pos + 1] == 0x80 and data[pos + 7] == 0x81)))

def inspect(data: bytes) -> tuple[Counter[str], int, list[str]]:
    counts: Counter[str] = Counter()
    warnings: list[str] = []
    line_count = 0
    matches = list(FONT_PATTERN.finditer(data))
    if not matches:
        warnings.append("Kein bekanntes Schriftformat gefunden: nicht als 0 Zeichen interpretieren.")
    for match in matches:
        font = match.group(1).decode("ascii")
        pos = match.start() + FIRST_CHAR_OFFSET
        if not valid_record(data, pos):
            warnings.append(f"{font} bei Offset {match.start()}: unbekannte Struktur, nicht gezählt.")
            continue
        n = 0
        while valid_record(data, pos) and n < 10000:
            if data[pos] != SPACE_CODE:
                counts[font] += 1
            n += 1
            pos += STRIDE
        line_count += 1
        if n == 10000:
            warnings.append(f"{font}: Sicherheitslimit erreicht; möglicherweise unvollständig.")
    return counts, line_count, warnings

def run_file(path: Path) -> str:
    counts, lines, warnings = inspect(path.read_bytes())
    result = [f"Datei: {path.name}", "", "Schriftsatz                  Zeichen", "-" * 42]
    for font, count in sorted(counts.items(), key=lambda x: x[0].casefold()):
        result.append(f"{font:<26}{count:>8}")
    result.extend(["-" * 42, f"Gesamt: {sum(counts.values())} Zeichen",
                   f"Erkannte Textzeilen: {lines}"])
    if warnings:
        result.extend(["", "WARNUNG: Ergebnis möglicherweise unvollständig!"] + warnings)
    result.extend(["", "Experimentell: nur bestätigte 106-Byte-Strukturen.",
                   "Leerzeichen (Byte FA) werden nicht gezählt."])
    return "\n".join(result)

def gui() -> None:
    root = tk.Tk()
    root.title("TB2-Textcounter – Prototyp")
    root.geometry("690x460")
    frame = ttk.Frame(root, padding=12)
    frame.pack(fill="both", expand=True)
    output = tk.Text(frame, wrap="word", font=("Consolas", 10), state="disabled")
    output.pack(fill="both", expand=True, pady=(10, 0))
    def open_file() -> None:
        filename = filedialog.askopenfilename(
            title="TB2-Datei auswählen",
            filetypes=[("Signum-Dateien", "*.tb2 *.tbl"), ("Alle Dateien", "*.*")])
        if not filename:
            return
        try:
            result = run_file(Path(filename))
        except (OSError, ValueError) as exc:
            messagebox.showerror("Fehler beim Lesen", str(exc))
            return
        output.configure(state="normal")
        output.delete("1.0", "end")
        output.insert("1.0", result)
        output.configure(state="disabled")
    ttk.Button(frame, text="TB2-Datei öffnen und zählen", command=open_file).pack(anchor="w")
    root.mainloop()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", nargs="?", type=Path)
    args = parser.parse_args()
    if args.file:
        print(run_file(args.file))
    else:
        gui()
