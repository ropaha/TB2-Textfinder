"""Identify source checkouts, Git archives and frozen builds."""
import json
import os
from pathlib import Path
import subprocess
import sys
from functools import lru_cache

ROOT = Path(__file__).resolve().parent.parent


def git(*args):
    try:
        return subprocess.check_output(
            ["git", "-C", str(ROOT), *args], stderr=subprocess.DEVNULL,
            text=True, timeout=3, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return ""


@lru_cache(maxsize=1)
def identity():
    if getattr(sys, "frozen", False):
        try:
            data = json.loads((Path(sys._MEIPASS) / "build_identity.json").read_text(encoding="utf-8"))
            return data["branch"], data["commit"]
        except (OSError, ValueError, KeyError, AttributeError):
            return "unbekannt", "unbekannt"
    branch = git("symbolic-ref", "--quiet", "--short", "HEAD") if (ROOT / ".git").exists() else ""
    commit = git("rev-parse", "--short=8", "HEAD") if (ROOT / ".git").exists() else ""
    if commit:
        return branch or "detached", commit
    try:
        lines = (ROOT / ".git-archive-info").read_text(encoding="utf-8").splitlines()
        commit = lines[0].strip()
        refs = lines[1].strip()
        if len(commit) == 40 and all(c in "0123456789abcdef" for c in commit):
            branches = [v.strip().removeprefix("HEAD -> ") for v in refs.split(",") if v.strip() and not v.strip().startswith("tag: ")]
            return (branches[0] if len(branches) == 1 else "unbekannt"), commit[:8]
    except (OSError, IndexError):
        pass
    return "unbekannt", "unbekannt"


def window_title(name, version):
    branch, _ = identity()
    return f"{name} – {version}" + (f" [{branch}]" if version.endswith("-dev") or branch not in ("main", "unbekannt") and branch.startswith("release/") else "")


def info_identity():
    branch, commit = identity()
    return f"Branch: {branch} | Commit: {commit}"
