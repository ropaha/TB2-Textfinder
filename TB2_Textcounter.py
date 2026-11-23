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

from tb2_muster import extract_counter_lines

SPACE_CODE = 0xFA


def inspect(data: bytes) -> tuple[Counter[str], int, list[str]]:
    lines, warnings = extract_counter_lines(data)
    counts: Counter[str] = Counter()
    for font, glyphs in lines:
        counts[font] += sum(code != SPACE_CODE for code in glyphs)
    return counts, len(lines), warnings

def run_file(path: Path) -> str:
    counts, lines, warnings = inspect(path.read_bytes())
    result = [f"Datei: {path.name}", "", "Schriftsatz                  Zeichen", "-" * 42]
    for font, count in sorted(counts.items(), key=lambda x: x[0].casefold()):
        result.append(f"{font:<26}{count:>8}")
    result.extend(["-" * 42, f"Gesamt: {sum(counts.values())} Zeichen",
                   f"Erkannte Textzeilen: {lines}"])
    if warnings:
        result.extend(["", "WARNUNG: Ergebnis möglicherweise unvollständig!"] + warnings)
    result.extend(["", "Experimentell: bekannte 80- und 106-Byte-Textstrukturen.",
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
