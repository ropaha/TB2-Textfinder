"""Local, read-only Signum regression inventory."""
import sys
import os
import json
import hashlib
import queue
import threading
from pathlib import Path
from collections import Counter
from time import perf_counter
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from TB2_Textcounter import counter_lines, SPACE_CODE, format_number, App as CounterApp
from tb2_window_position import center_window
from tb2_app_identity import configure_app_identity, apply_window_icon
from tb2_project_info import PROJECT_URL
import webbrowser
from tb2_muster import historical_resource_document
from tb2_version import APP_VERSION
from tb2_settings import load_folder, remember_folder, load_json_folder, remember_json_folder

def parser_hashes():
    base = Path(__file__).resolve().parents[1]
    names = ("TB2_Textcounter.py", "tb2_muster.py", "tb2_jpeg_fast.py", "tb2_resource_paths.py", "tools/Signum_Regressiontester.py")
    return {name: hashlib.sha256((base / name).read_bytes()).hexdigest()
            for name in names if (base / name).is_file()}

def compact_report(result):
    current = result["current"]
    rows = current["files"].values()
    summary = dict(file_count=len(current["files"]),
                   statuses=dict(Counter(row["status"] for row in rows)),
                   characters=sum(sum(row.get("fonts", {}).values()) for row in rows),
                   lines=sum(row.get("lines", 0) for row in rows),
                   bytes=sum(row.get("size", 0) for row in rows))
    return dict(report_type="compact_comparison", reference_version=result["reference_version"],
                reference_parser_hashes=result.get("reference_parser_hashes"),
                current={k: v for k, v in current.items() if k != "files"},
                summary=summary, changes=result["changes"])

def scan(root, mode, stop, notify):
    rows = {}
    errors = []
    paths = []
    started = perf_counter()
    hashes = parser_hashes()
    for base, dirs, names in os.walk(root, followlinks=False, onerror=lambda e: errors.append(str(e))):
        if stop.is_set():
            return None
        dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(base, d))
                   and not getattr(os.path, "isjunction", lambda p: False)(os.path.join(base, d))]
        paths.extend(Path(base)/n for n in names if Path(n).suffix.lower() in (".tb2", ".tbl")
                     and not (Path(base)/n).is_symlink())
    for i, path in enumerate(sorted(paths), 1):
        if stop.is_set():
            return None
        key = path.relative_to(root).as_posix()
        t = perf_counter()
        row = {}
        try:
            data = path.read_bytes()
            row["sha256"] = hashlib.sha256(data).hexdigest()
            row["size"] = len(data)
            resources = historical_resource_document(data)
            lines, warnings = ([], []) if resources is not None else counter_lines(data, mode)
            counts = Counter()
            sequence = hashlib.sha256()
            for font, glyphs in lines:
                counts[font.upper()] += sum(c != SPACE_CODE for c in glyphs)
                sequence.update(json.dumps([font.upper(), list(glyphs)], ensure_ascii=True, separators=(",", ":")).encode("ascii"))
                sequence.update(b"\n")
            row.update(fonts=dict(counts), lines=len(lines), warnings=warnings,
                       sequence_sha256=sequence.hexdigest(),
                       status="Ressourcen" if resources is not None else
                       "Leer" if not data else "Prüfen" if warnings or not lines else "Gezählt")
        except Exception as exc:
            row.update(status="Fehler", error=str(exc))
        row["seconds"] = perf_counter()-t
        rows[key] = row
        if i == 1 or i % 10 == 0 or i == len(paths):
            notify(("progress", i, len(paths)))
    return dict(schema=1, version=APP_VERSION, mode=mode, root=str(root),
                seconds=perf_counter()-started, walk_errors=errors, files=rows, parser_hashes=hashes)

def compare(old, new):
    if old["schema"] != new["schema"] or old["mode"] != new["mode"]:
        raise ValueError("Referenzschema oder Suchmodus stimmt nicht überein.")
    a, b = old["files"], new["files"]
    changes = []
    for key in sorted(a.keys() | b.keys()):
        x, y = a.get(key), b.get(key)
        if x is None:
            kind = "Neue Datei"
        elif y is None:
            kind = "Fehlende Datei"
        elif x.get("status") == "Fehler" or y.get("status") == "Fehler":
            kind = "Lesefehler"
        elif x.get("sha256") != y.get("sha256"):
            kind = "Datei verändert"
        elif (any(x.get(k) != y.get(k) for k in ("fonts", "lines", "warnings", "status"))
              or (x.get("sequence_sha256") is not None and y.get("sequence_sha256") is not None
                  and x["sequence_sha256"] != y["sequence_sha256"])):
            kind = ("Neu erkannt" if x["status"] == "Prüfen" and y["status"] == "Gezählt"
                    else "Nicht mehr sicher erkannt" if x["status"] == "Gezählt" and y["status"] != "Gezählt"
                    else "Ergebnis verändert")
        else:
            continue
        changes.append(dict(path=key, category=kind, before=x, after=y))
    return changes

def save_new(path, root, payload):
    path = Path(path).resolve()
    if path == root or root in path.parents or path.suffix.lower() != ".json":
        raise ValueError("JSON-Datei außerhalb des Quellordners wählen.")
    with path.open("x", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

class App(tk.Tk):
    def __init__(self):
        configure_app_identity("ropaha.SignumRegressiontester")
        super().__init__()
        apply_window_icon(self)
        self.title("Signum Regressionstester – " + APP_VERSION)
        center_window(self, 950, 600)
        self.minsize(720, 480)
        self.rootdir = tk.StringVar(value=load_folder())
        self.mode = tk.StringVar(value="fast")
        self.status = tk.StringVar(value="Quellordner wählen.")
        self.events = queue.Queue()
        self.stop = threading.Event()
        self.running = False
        self.result = None
        frame = ttk.Frame(self, padding=14)
        frame.pack(fill="both", expand=True)
        folder = ttk.Frame(frame)
        folder.pack(fill="x")
        ttk.Label(folder, text="Ordner:").pack(side="left")
        self.entry = ttk.Entry(folder, textvariable=self.rootdir)
        self.entry.pack(side="left", fill="x", expand=True, padx=10)
        self.choose = ttk.Button(folder, text="Ordner wählen …", command=self.pick)
        self.choose.pack(side="right")
        self.controls = [self.choose, self.entry]
        modes = ttk.Frame(frame)
        modes.pack(fill="x", pady=(10, 2))
        ttk.Label(modes, text="Suchmodus:").pack(side="left", padx=(0,10))
        for label, value in [("Schnell (JPEG überspringen)", "fast"), ("Vollständig (alle Bytes)", "full")]:
            w = ttk.Radiobutton(modes, text=label, variable=self.mode, value=value)
            w.pack(side="left", padx=(0,14))
            self.controls.append(w)
        bar = ttk.Frame(frame)
        bar.pack(fill="x", pady=(12,10))
        for label, cmd in [("Referenz erstellen", lambda: self.start(False)), ("Vergleichen", lambda: self.start(True))]:
            w = ttk.Button(bar, text=label, command=cmd)
            w.pack(side="left", padx=(0,8))
            self.controls.append(w)
        self.open_button = ttk.Button(bar, text="Öffnen", command=self.open_selected, state="disabled")
        self.open_button.pack(side="left", padx=(0,8))
        self.cancel = ttk.Button(bar, text="Abbrechen", command=self.stop.set, state="disabled")
        self.cancel.pack(side="left", padx=(0,8))
        self.save = ttk.Button(bar, text="JSON speichern", command=self.export, state="disabled")
        self.save.pack(side="left")
        self.compact = ttk.Button(bar, text="Kompakt", command=lambda: self.export(True), state="disabled")
        self.compact.pack(side="left", padx=(8,0))
        self.progress = ttk.Progressbar(frame, mode="determinate")
        self.progress.pack(fill="x", pady=(0,7))
        ttk.Label(frame, textvariable=self.status, wraplength=880).pack(fill="x")
        filters = ttk.Frame(frame)
        filters.pack(fill="x", pady=(4,8))
        ttk.Label(filters, text="Filter:").pack(side="left")
        self.filter = ttk.Combobox(filters, state="readonly", values=("Alle",), width=32)
        self.filter.set("Alle")
        self.filter.pack(side="left", padx=8)
        self.filter.bind("<<ComboboxSelected>>", lambda _: self.render_results())
        footer = ttk.Frame(frame)
        footer.pack(side="bottom", fill="x", pady=(10,0))
        ttk.Button(footer, text="Programm beenden", command=self.close).pack(side="right")
        ttk.Button(footer, text="Info", command=self.show_info).pack(side="right", padx=(0,8))
        results = ttk.Frame(frame)
        results.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(results, columns=("category","path","old","new"), show="headings")
        for k, label, width in [("category","Kategorie",180),("path","Datei",420),("old","Vorher",90),("new","Nachher",90)]:
            self.tree.heading(k,text=label)
            self.tree.column(k,width=width, anchor="e" if k in ("old","new") else "w")
        scrollbar = ttk.Scrollbar(results, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", lambda _: self.open_button.configure(state="normal" if self.tree.selection() and not self.running else "disabled"))
        self.tree.bind("<Double-1>", lambda _: self.open_selected())
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.after(100,self.poll)
    show_license = CounterApp.show_license
    show_changelog = CounterApp.show_changelog

    def show_info(self):
        dialog = tk.Toplevel(self)
        dialog.title("Info – Signum Regressionstester")
        center_window(dialog, 650, 380, parent=self)
        dialog.transient(self)
        body = ttk.Frame(dialog, padding=18)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Signum Regressionstester – Version " + APP_VERSION,
                  font=("TkDefaultFont", 13, "bold")).pack(anchor="w", pady=(0,12))
        ttk.Label(body, text="Vergleicht die Erkennung von TB2- und TBL-Dateien mit einer gespeicherten Referenz. Unterordner werden immer einbezogen. Quelldateien werden ausschließlich gelesen. JSON-Berichte werden außerhalb des Quellordners gespeichert.", wraplength=590).pack(anchor="w")
        buttons = ttk.Frame(body)
        buttons.pack(side="bottom", fill="x")
        ttk.Button(buttons, text="GitHub", command=lambda: webbrowser.open(PROJECT_URL)).pack(side="left")
        ttk.Button(buttons, text="MIT-Lizenz", command=lambda: self.show_license(dialog)).pack(side="left", padx=8)
        ttk.Button(buttons, text="Schließen", command=dialog.destroy).pack(side="right")

    def open_selected(self):
        if self.running or not self.result or not self.tree.selection():
            return
        rel = self.tree.item(self.tree.selection()[0], "values")[1]
        path = (self.source / rel).resolve()
        if self.source not in path.parents or not path.is_file():
            messagebox.showwarning("Öffnen", "Datei nicht vorhanden oder außerhalb des Quellordners.", parent=self)
            return
        try:
            os.startfile(str(path))
        except (OSError, AttributeError) as exc:
            messagebox.showerror("Öffnen", str(exc), parent=self)

    def render_results(self):
        self.tree.delete(*self.tree.get_children())
        self.open_button.configure(state="disabled")
        for c in (self.result or {}).get("changes", []):
            if self.filter.get() not in ("Alle", c["category"]):
                continue
            total = lambda r: format_number(sum((r or {}).get("fonts", {}).values()))
            self.tree.insert("", "end", values=(c["category"], c["path"], total(c["before"]), total(c["after"])))

    def pick(self):
        p = filedialog.askdirectory(title="Ordner mit TB2-/TBL-Dateien auswählen", initialdir=self.rootdir.get() or None)
        if p:
            self.rootdir.set(p)
            remember_folder(p)
    def close(self):
        if self.running:
            self.stop.set()
            self.status.set("Abbruch angefordert. Nach Ende erneut schließen.")
        else:
            self.destroy()
    def start(self, comparison):
        if self.running: return
        if not self.rootdir.get().strip() or not Path(self.rootdir.get()).is_dir():
            messagebox.showerror("Ordner", "Gültigen Quellordner wählen.")
            return
        root = Path(self.rootdir.get()).resolve()
        mode = self.mode.get()
        remember_folder(root)
        old = None
        if comparison:
            p = filedialog.askopenfilename(filetypes=[("JSON","*.json")], initialdir=load_json_folder() or None)
            if not p: return
            try:
                with open(p,encoding="utf-8") as f: old = json.load(f)
                if old["schema"] != 1 or old["mode"] != mode or Path(old["root"]).resolve() != root:
                    raise ValueError("Referenz, Ordner oder Suchmodus passt nicht.")
            except Exception as e:
                messagebox.showerror("Referenz",str(e))
                return
        self.running = True
        self.cancel.configure(state="normal")
        self.open_button.configure(state="disabled")
        self.filter.configure(values=("Alle",))
        self.filter.set("Alle")
        self.filter.configure(state="disabled")
        self.stop.clear()
        self.result = None
        self.save.configure(state="disabled")
        self.compact.configure(state="disabled")
        for w in self.controls: w.configure(state="disabled")
        self.tree.delete(*self.tree.get_children())
        self.status.set("Dateien werden ermittelt …")
        self.progress.configure(value=0)
        def worker():
            try:
                new = scan(root,mode,self.stop,self.events.put)
                if new is None or self.stop.is_set():
                    self.events.put(("done",None,root))
                else:
                    result = new if old is None else dict(reference_version=old["version"], reference_parser_hashes=old.get("parser_hashes"), current=new, changes=compare(old,new))
                    self.events.put(("done",result,root))
            except Exception as e:
                self.events.put(("error",str(e)))
        threading.Thread(target=worker,daemon=True).start()
    def poll(self):
        try:
            while True:
                e = self.events.get_nowait()
                if e[0] == "progress":
                    self.progress.configure(maximum=max(1,e[2]),value=e[1])
                    self.status.set(f"{format_number(e[1])} von {format_number(e[2])} Dateien analysiert ({format_number(100 * e[1] / e[2], 1)} %)")
                else:
                    self.running = False
                    self.filter.configure(state="readonly")
                    self.cancel.configure(state="disabled")
                    for w in self.controls: w.configure(state="normal")
                    if e[0] == "error":
                        self.status.set(e[1])
                        continue
                    self.result,self.source = e[1:]
                    if self.result is None:
                        self.status.set("Abgebrochen – kein Ergebnis gespeichert.")
                        continue
                    self.save.configure(state="normal")
                    self.compact.configure(state="normal" if "changes" in self.result else "disabled")
                    current = self.result.get("current",self.result)
                    changes = self.result.get("changes",[])
                    counts = Counter(c["category"] for c in changes)
                    self.status.set(f'{len(current["files"])} Dateien | {current["seconds"]:.2f} s | {len(current["walk_errors"])} Ordnerfehler | ' + (str(dict(counts)) if "changes" in self.result else "Referenz bereit"))
                    self.filter.configure(values=("Alle", *sorted(counts)))
                    self.render_results()
        except queue.Empty:
            pass
        self.after(100,self.poll)
    def export(self, compact=False):
        p = filedialog.asksaveasfilename(defaultextension=".json",filetypes=[("JSON","*.json")], initialdir=load_json_folder() or None)
        if p:
            try:
                save_new(p,self.source,compact_report(self.result) if compact else self.result)
                remember_json_folder(Path(p).resolve().parent)
                self.status.set("Gespeichert: "+p)
            except Exception as e:
                messagebox.showerror("Speichern",str(e))

if __name__ == "__main__":
    App().mainloop()
