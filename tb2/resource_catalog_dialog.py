"""Shared non-modal resource inventory dialog."""
import threading
import queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from .resource_catalog import EXTENSIONS, load_catalog, scan_resources, save_catalog
from .settings import load_option, remember_directory, load_export_folder, remember_export_folder

def show_resource_catalog(parent):
    existing = getattr(parent, "_resource_dialog", None)
    if existing is not None and existing.winfo_exists():
        existing.lift()
        return
    dialog = tk.Toplevel(parent)
    parent._resource_dialog = dialog
    dialog.title("Signum-Ressourcen")
    dialog.transient(parent)
    body = ttk.Frame(dialog, padding=12)
    body.pack(fill="both", expand=True)
    data = load_catalog()
    root = tk.StringVar(value=load_option("resource_folder", "") or (data or {}).get("resource_root", ""))
    status = tk.StringVar()
    ttk.Label(body, text="Ressourcenordner (inkl. Unterordner)").pack(anchor="w")
    row = ttk.Frame(body)
    row.pack(fill="x", pady=5)
    entry = ttk.Entry(row, textvariable=root, width=55)
    entry.pack(side="left", fill="x", expand=True)
    def choose():
        folder = filedialog.askdirectory(parent=dialog, initialdir=root.get() or None)
        if folder:
            root.set(folder)
    choose_button = ttk.Button(row, text="Ordner wählen …", command=choose)
    choose_button.pack(side="left", padx=(5, 0))
    tree = ttk.Treeview(body, columns=("type", "count", "unique"), show="headings", height=6)
    tree.heading("type", text="Dateityp")
    tree.heading("count", text="Anzahl")
    tree.heading("unique", text="Unterschiedliche Inhalte")
    tree.column("unique", width=180, anchor="e")
    tree.column("type", width=160)
    tree.column("count", width=100, anchor="e")
    tree.pack(fill="x", pady=5)
    ttk.Label(body, textvariable=status, wraplength=480).pack(anchor="w", pady=5)
    progress_bar = ttk.Progressbar(body, mode="determinate")
    progress_bar.pack(fill="x", pady=(0, 5))
    actions = ttk.Frame(body)
    actions.pack(fill="x")
    results = queue.Queue()
    progress_updates = queue.Queue(maxsize=1)
    running = False
    def refresh():
        tree.delete(*tree.get_children())
        for ext in EXTENSIONS:
            entries = data["resources"].get(ext, []) if data else []
            unique = len({item["sha256"] for item in entries}) if data and data.get("schema") == 2 else "–"
            tree.insert("", "end", values=(ext, len(entries), unique))
        status.set(("Katalog: " + data["resource_root"] + "\nStand: " + data["created_at"] +
                    " | Zugriffsprobleme: " + str(len(data.get("errors", [])))) if data else "Noch kein Katalog vorhanden.")
        if data and data.get("schema") == 1:
            status.set(status.get() + "\nNoch ohne Prüfsummen – bitte neu erfassen.")
        export_button.configure(state="normal" if data else "disabled")
    def report_progress(done, total):
        try:
            progress_updates.get_nowait()
        except queue.Empty:
            pass
        progress_updates.put_nowait((done, total))
    def worker(folder):
        try:
            result = scan_resources(folder, progress=report_progress)
            save_catalog(result)
            results.put((result, None))
        except Exception as exc:
            results.put((None, str(exc)))
    def poll():
        nonlocal data, running
        try:
            done, total = progress_updates.get_nowait()
            progress_bar.stop()
            progress_bar.configure(mode="determinate", maximum=max(total, 1), value=done)
            status.set(f"Prüfsummen: {done:,} / {total:,}".replace(",", "."))
        except queue.Empty:
            pass
        try:
            result, error = results.get_nowait()
        except queue.Empty:
            dialog.after(100, poll)
            return
        running = False
        progress_bar.stop()
        progress_bar.configure(mode="determinate", value=0)
        for widget in (entry, choose_button, scan_button):
            widget.configure(state="normal")
        if error is not None:
            messagebox.showerror("Ressourcenkatalog", error, parent=dialog)
        else:
            data = result
            remember_directory("resource_folder", data["resource_root"])
        refresh()
    def scan():
        nonlocal running
        if not root.get().strip():
            messagebox.showwarning("Ressourcenkatalog", "Bitte einen Ordner auswählen.", parent=dialog)
            return
        running = True
        for widget in (entry, choose_button, scan_button, export_button):
            widget.configure(state="disabled")
        status.set("Ressourcendateien werden gesucht …")
        progress_bar.configure(mode="indeterminate")
        progress_bar.start(15)
        threading.Thread(target=worker, args=(root.get(),), daemon=True).start()
        dialog.after(100, poll)
    def export():
        path = filedialog.asksaveasfilename(parent=dialog, initialdir=load_export_folder() or None,
                                            initialfile="resources.json", defaultextension=".json",
                                            filetypes=[("JSON", "*.json")])
        if path:
            try:
                save_catalog(data, path)
                from pathlib import Path
                remember_export_folder(Path(path).parent)
            except OSError as exc:
                messagebox.showerror("Export", str(exc), parent=dialog)
    def close():
        if running:
            messagebox.showinfo("Ressourcenkatalog", "Bitte die Erfassung abwarten.", parent=dialog)
        else:
            dialog.destroy()
    scan_button = ttk.Button(actions, text="Ressourcen erfassen", command=scan)
    scan_button.pack(side="left")
    export_button = ttk.Button(actions, text="Katalog exportieren …", command=export)
    export_button.pack(side="left", padx=5)
    ttk.Button(actions, text="Schließen", command=close).pack(side="right")
    dialog.protocol("WM_DELETE_WINDOW", close)
    refresh()
