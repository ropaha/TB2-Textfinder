"""Read-only experimental Signum inventory counter."""
from __future__ import annotations
import os
import queue
import threading
from collections import Counter, defaultdict
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from tb2_muster import extract_counter_lines

SPACE_CODE = 0xFA

def scan(root, recursive, stop, events):
    counts = defaultdict(Counter)
    files = lines_total = uncertain = errors = 0
    def walk_error(exc):
        events.put(("error", str(exc)))
    try:
        for base, dirs, names in os.walk(root, followlinks=False, onerror=walk_error):
            dirs[:] = [d for d in dirs if recursive and not os.path.islink(os.path.join(base,d))
                       and not getattr(os.path, "isjunction", lambda p: False)(os.path.join(base,d))]
            for name in names:
                if stop.is_set():
                    return
                path = Path(base) / name
                if path.suffix.lower() not in (".tb2", ".tbl") or path.is_symlink():
                    continue
                files += 1
                try:
                    with path.open("rb") as source:
                        lines, warnings = extract_counter_lines(source.read())
                    lines_total += len(lines)
                    if warnings or not lines:
                        uncertain += 1
                    for font, glyphs in lines:
                        counts[font].update(c for c in glyphs if c != SPACE_CODE)
                except Exception as exc:
                    errors += 1
                    events.put(("error", f"{path}: {exc}"))
                if files % 10 == 0:
                    events.put(("progress", files))
    finally:
        events.put(("done", dict(counts), files, lines_total, uncertain, errors, stop.is_set()))

def glyph_label(code):
    if 32 <= code <= 126:
        return chr(code)
    return f"0x{code:02X} (Kodierung ungeklärt)"

def gui():
    root = tk.Tk()
    root.title("Signum Textcounter – Bestandsauswertung (RO, experimentell)")
    root.geometry("900x650")
    folder = tk.StringVar()
    recursive = tk.BooleanVar(value=True)
    status = tk.StringVar(value="Bitte einen separaten Testordner mit Kopien auswählen.")
    events = queue.Queue()
    stop = threading.Event()
    running = False
    top = ttk.Frame(root, padding=12)
    top.pack(fill="x")
    ttk.Entry(top, textvariable=folder).pack(side="left", fill="x", expand=True)
    def choose():
        selected = filedialog.askdirectory()
        if selected:
            folder.set(selected)
    choose_button = ttk.Button(top, text="Ordner wählen …", command=choose)
    choose_button.pack(side="left", padx=8)
    bar = ttk.Frame(root, padding=(12,0))
    bar.pack(fill="x")
    check = ttk.Checkbutton(bar, text="Unterordner einbeziehen", variable=recursive)
    check.pack(side="left")
    tree = ttk.Treeview(root, columns=("count",), show="tree headings")
    tree.heading("#0", text="Schriftart / Zeichen")
    tree.heading("count", text="Anzahl")
    tree.column("count", width=120, anchor="e")
    tree.pack(fill="both", expand=True, padx=12, pady=8)
    ttk.Label(root, textvariable=status, wraplength=850, padding=12).pack(fill="x")
    def start():
        nonlocal running
        if running:
            stop.set()
            status.set("Abbruch angefordert …")
            return
        if not folder.get().strip() or not Path(folder.get()).is_dir():
            messagebox.showwarning("Ordner fehlt", "Bitte einen gültigen Testordner auswählen.")
            return
        if not messagebox.askyesno("Testversion", "Nur mit isolierten Kopien testen. Ist dies ein separater Testordner?", default="no"):
            return
        running = True
        stop.clear()
        for item in tree.get_children():
            tree.delete(item)
        button.configure(text="Abbrechen")
        choose_button.configure(state="disabled")
        check.configure(state="disabled")
        status.set("Prüfung läuft …")
        threading.Thread(target=scan, args=(Path(folder.get()), recursive.get(), stop, events), daemon=True).start()
    button = ttk.Button(bar, text="Zählen", command=start)
    button.pack(side="left", padx=8)
    issues = []
    def poll():
        nonlocal running
        try:
            while True:
                event = events.get_nowait()
                if event[0] == "progress":
                    status.set(f"{event[1]} Dateien untersucht …")
                elif event[0] == "error":
                    issues.append(event[1])
                elif event[0] == "done":
                    _, counts, files, lines, uncertain, errors, cancelled = event
                    total = sum(sum(c.values()) for c in counts.values())
                    tree.insert("", "end", text="GESAMT (erkannte Zeichen)", values=(total,))
                    for font, chars in sorted(counts.items(), key=lambda x:x[0].casefold()):
                        node = tree.insert("", "end", text=font, values=(sum(chars.values()),))
                        for code, count in sorted(chars.items()):
                            tree.insert(node, "end", text=glyph_label(code), values=(count,))
                    status.set(f"{'Abgebrochen' if cancelled else 'Fertig'}: {files} Dateien | {len(counts)} Schriftbezeichnungen | {lines} Zeilen | {total} Zeichen ohne Leerzeichen | {uncertain} unsichere Dateien | {errors} Dateifehler | {len(issues)} Fehlermeldungen. Ergebnis möglicherweise unvollständig.")
                    issues.clear()
                    running = False
                    button.configure(text="Zählen")
                    choose_button.configure(state="normal")
                    check.configure(state="normal")
        except queue.Empty:
            pass
        root.after(100, poll)
    root.after(100, poll)
    root.mainloop()

if __name__ == "__main__":
    gui()
