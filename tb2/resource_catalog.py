"""Optional local inventory; never used to classify TB2 documents."""
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from .settings import settings_path

EXTENSIONS = ("FNT", "FN2", "FN3", "ORN", "BAU", "STN")

def catalog_path():
    return settings_path().with_name("resources.json")

def scan_resources(root):
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise NotADirectoryError(root)
    resources = {ext: [] for ext in EXTENSIONS}
    errors = []
    for folder, dirs, files in os.walk(root, followlinks=False, onerror=lambda e: errors.append(str(e))):
        dirs.sort(key=str.casefold)
        for name in sorted(files, key=str.casefold):
            path = Path(folder) / name
            ext = path.suffix[1:].upper()
            if ext not in resources:
                continue
            try:
                resources[ext].append({"name": name, "path": path.relative_to(root).as_posix(), "size": path.stat().st_size})
            except OSError as exc:
                errors.append(str(exc))
    return {"schema": 1, "resource_root": str(root),
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
        if isinstance(data, dict) and data.get("schema") == 1 and isinstance(data.get("resources"), dict):
            return data
    except (OSError, ValueError):
        pass
    return None
