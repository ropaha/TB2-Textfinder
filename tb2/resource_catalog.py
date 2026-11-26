"""Optional local inventory; never used to classify TB2 documents."""
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from .settings import settings_path

EXTENSIONS = ("FNT", "FN2", "FN3", "ORN", "BAU", "STN")

def catalog_path():
    return settings_path().with_name("resources.json")

def scan_resources(root, progress=None):
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise NotADirectoryError(root)
    resources = {ext: [] for ext in EXTENSIONS}
    errors = []
    candidates = []
    for folder, dirs, files in os.walk(root, followlinks=False, onerror=lambda e: errors.append(str(e))):
        dirs.sort(key=str.casefold)
        for name in sorted(files, key=str.casefold):
            path = Path(folder) / name
            ext = path.suffix[1:].upper()
            if ext not in resources:
                continue
            candidates.append((ext, path))
    total = len(candidates)
    if progress:
        progress(0, total)
    for index, (ext, path) in enumerate(candidates, 1):
        try:
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                before = os.fstat(stream.fileno())
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(block)
                after = os.fstat(stream.fileno())
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                raise OSError(f"File changed during scan: {path}")
            resources[ext].append({"name": path.name, "path": path.relative_to(root).as_posix(),
                                   "size": after.st_size, "sha256": digest.hexdigest()})
        except OSError as exc:
            errors.append(f"{path}: {exc}")
        if progress:
            progress(index, total)
    return {"schema": 2, "resource_root": str(root),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "resources": resources, "errors": errors}

def save_catalog(data, path=None):
    path = Path(path) if path is not None else catalog_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".resources-", suffix=".tmp", delete=False) as f:
            temporary = Path(f.name)
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)

def load_catalog():
    try:
        data = json.loads(catalog_path().read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("schema") in (1, 2) and isinstance(data.get("resources"), dict):
            return data
    except (OSError, ValueError):
        pass
    return None
