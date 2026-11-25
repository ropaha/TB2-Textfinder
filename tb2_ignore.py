"""Central ignore list; legacy lists are read only."""
import hashlib
import json
import os
import tempfile
from pathlib import Path
from tb2_settings import settings_path

def path_key(path):
    return os.path.normcase(os.path.abspath(path))

def ignore_path():
    return settings_path().with_name("TB2-Ignore.json")

def fingerprint(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def load():
    try:
        data = json.loads(ignore_path().read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"schema": 1, "files": {}, "imported": []}
    if (not isinstance(data, dict) or data.get("schema") != 1
            or not isinstance(data.get("files"), dict)
            or not isinstance(data.get("imported"), list)
            or not all(isinstance(k, str) and isinstance(v, str) for k, v in data["files"].items())
            or not all(isinstance(k, str) for k in data["imported"])):
        raise ValueError("Ungültige zentrale Ignorierliste.")
    return data

def save(data, protected_root):
    path = ignore_path().resolve()
    root = Path(protected_root).resolve()
    if path == root or root in path.parents:
        raise ValueError("Ignorierliste darf nicht im Quellordner liegen.")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".ignore-", suffix=".tmp", delete=False) as f:
            temporary = Path(f.name)
            json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)

def import_legacy(data, directories, root, stop, skipped):
    imported = set(data["imported"])
    changed = False
    for directory in sorted(directories):
        if stop.is_set():
            break
        legacy = directory / "ignore.txt"
        key = path_key(legacy)
        if key in imported:
            continue
        try:
            if not legacy.is_file():
                continue
            additions = {}
            for line in legacy.read_text(encoding="utf-8").splitlines():
                if stop.is_set():
                    break
                name = line.strip()
                if not name or name.startswith("#"):
                    continue
                candidate = directory / name
                if Path(name).name != name or candidate.suffix.lower() not in (".tb2", ".tbl"):
                    raise ValueError("Ungültiger Dateiname: " + name)
                if candidate.is_file():
                    k = path_key(candidate)
                    if k not in data["files"]:
                        additions[k] = fingerprint(candidate)
            if stop.is_set():
                break
            data["files"].update(additions)
            imported.add(key)
            changed = True
        except (OSError, ValueError) as exc:
            skipped.append(f"{legacy}: {exc}")
    if changed:
        data["imported"] = sorted(imported)
        save(data, root)

def matching(data, path):
    expected = data["files"].get(path_key(path))
    return expected is not None and fingerprint(path) == expected

def toggle(paths, should_ignore, root):
    data = load()
    for path in paths:
        key = path_key(path)
        if should_ignore:
            data["files"][key] = fingerprint(path)
        else:
            data["files"].pop(key, None)
    save(data, root)
