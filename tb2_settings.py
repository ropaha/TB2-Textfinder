"""Shared per-user settings for the Signum Textfinder tools."""
import json
import os
import tempfile
from pathlib import Path

def settings_path():
    return Path(os.environ.get("LOCALAPPDATA") or Path.home() / ".config") / "Signum Textfinder" / "TB2-Textfinder.json"

def load_settings():
    path = settings_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        legacy = path.parent.parent / "SignumRegressiontester" / "settings.json"
        try:
            data = json.loads(legacy.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
    except (OSError, ValueError):
        data = {}
    return data if isinstance(data, dict) else {}

def load_folder():
    folder = load_settings().get("folder", "")
    return folder if isinstance(folder, str) else ""

def remember_folder(folder):
    remember_directory("folder", folder)

def load_json_folder():
    folder = load_settings().get("regression_json_folder", "")
    return folder if isinstance(folder, str) and Path(folder).is_dir() else ""

def remember_json_folder(folder):
    remember_directory("regression_json_folder", folder)

def remember_directory(key, folder):
    path = settings_path()
    temporary = None
    try:
        folder = Path(folder).resolve()
        if not folder.is_dir() or path.resolve() == folder or folder in path.resolve().parents:
            return
        data = load_settings()
        data[key] = str(folder)
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".settings-", suffix=".tmp", delete=False) as f:
            temporary = Path(f.name)
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(temporary, path)
    except (OSError, ValueError):
        pass
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
