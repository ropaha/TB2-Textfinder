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
from TB2_Textcounter import counter_lines, SPACE_CODE
from tb2_muster import historical_resource_document
from tb2_version import APP_VERSION

def scan(root, mode, stop, notify):
    rows = {}
    errors = []
    paths = []
    started = perf_counter()
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
            for font, glyphs in lines:
                counts[font.upper()] += sum(c != SPACE_CODE for c in glyphs)
            row.update(fonts=dict(counts), lines=len(lines), warnings=warnings,
                       status="Ressourcen" if resources is not None else
                       "Leer" if not data else "Prüfen" if warnings or not lines else "Gezählt")
        except Exception as exc:
            row.update(status="Fehler", error=str(exc))
        row["seconds"] = perf_counter()-t
        rows[key] = row
        if i == 1 or i % 10 == 0 or i == len(paths):
            notify(("progress", i, len(paths)))
    return dict(schema=1, version=APP_VERSION, mode=mode, root=str(root),
                seconds=perf_counter()-started, walk_errors=errors, files=rows)

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
        elif any(x.get(k) != y.get(k) for k in ("fonts", "lines", "warnings", "status")):
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
        super().__init__()
        self.title("Signum Regressionstester – " + APP_VERSION)
        self.geometry("950x600")
        self.rootdir = tk.StringVar()
        self.mode = tk.StringVar(value="fast")
        self.status = tk.StringVar(value="Quellordner wählen.")
        self.events = queue.Queue()
        self.stop = threading.Event()
        self.running = False
        self.result = None
        frame = ttk.Frame(self, padding=14)
        frame.pack(fill="both", expand=True)
        ttk.Entry(frame, textvariable=self.rootdir).pack(fill="x")
        self.choose = ttk.Button(frame, text="Ordner wählen", command=self.pick)
        self.choose.pack(anchor="w")
        self.controls = [self.choose]
        for label, value in [("Schnell (JPEG überspringen)", "fast"), ("Vollständig", "full")]:
            w = ttk.Radiobutton(frame, text=label, variable=self.mode, value=value)
            w.pack(anchor="w")
            self.controls.append(w)
        bar = ttk.Frame(frame)
        bar.pack(fill="x", pady=8)
        for label, cmd in [("Referenz erstellen", lambda: self.start(False)), ("Vergleichen", lambda: self.start(True))]:
            w = ttk.Button(bar, text=label, command=cmd)
            w.pack(side="left", padx=4)
            self.controls.append(w)
        ttk.Button(bar, text="Abbrechen", command=self.stop.set).pack(side="left")
        self.save = ttk.Button(bar, text="JSON speichern", command=self.export, state="disabled")
        self.save.pack(side="left")
        self.progress = ttk.Progressbar(frame)
        self.progress.pack(fill="x")
        ttk.Label(frame, textvariable=self.status, wraplength=880).pack(fill="x")
        self.tree = ttk.Treeview(frame, columns=("category","path","old","new"), show="headings")
        for k, label, width in [("category","Kategorie",180),("path","Datei",420),("old","Vorher",90),("new","Nachher",90)]:
            self.tree.heading(k,text=label)
            self.tree.column(k,width=width)
        self.tree.pack(fill="both", expand=True)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.after(100,self.poll)
    def pick(self):
        p = filedialog.askdirectory()
        if p: self.rootdir.set(p)
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
        old = None
        if comparison:
            p = filedialog.askopenfilename(filetypes=[("JSON","*.json")])
            if not p: return
            try:
                with open(p,encoding="utf-8") as f: old = json.load(f)
                if old["schema"] != 1 or old["mode"] != mode or Path(old["root"]).resolve() != root:
                    raise ValueError("Referenz, Ordner oder Suchmodus passt nicht.")
            except Exception as e:
                messagebox.showerror("Referenz",str(e))
                return
        self.running = True
        self.stop.clear()
        self.result = None
        self.save.configure(state="disabled")
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
                    result = new if old is None else dict(reference_version=old["version"], current=new, changes=compare(old,new))
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
                    self.status.set(f"{e[1]} / {e[2]} Dateien")
                else:
                    self.running = False
                    for w in self.controls: w.configure(state="normal")
                    if e[0] == "error":
                        self.status.set(e[1])
                        continue
                    self.result,self.source = e[1:]
                    if self.result is None:
                        self.status.set("Abgebrochen – kein Ergebnis gespeichert.")
                        continue
                    self.save.configure(state="normal")
                    current = self.result.get("current",self.result)
                    changes = self.result.get("changes",[])
                    counts = Counter(c["category"] for c in changes)
                    self.status.set(f'{len(current["files"])} Dateien | {current["seconds"]:.2f} s | {len(current["walk_errors"])} Ordnerfehler | ' + (str(dict(counts)) if "changes" in self.result else "Referenz bereit"))
                    for c in changes:
                        total = lambda r: sum((r or {}).get("fonts",{}).values())
                        self.tree.insert("","end",values=(c["category"],c["path"],total(c["before"]),total(c["after"])))
        except queue.Empty:
            pass
        self.after(100,self.poll)
    def export(self):
        p = filedialog.asksaveasfilename(defaultextension=".json",filetypes=[("JSON","*.json")])
        if p:
            try:
                save_new(p,self.source,self.result)
                self.status.set("Gespeichert: "+p)
            except Exception as e:
                messagebox.showerror("Speichern",str(e))

if __name__ == "__main__":
    App().mainloop()
