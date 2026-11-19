"""Offline-Versionsverlauf aus der mitgelieferten CHANGELOG.md."""
from pathlib import Path
import re
import sys

SECTION = re.compile(r"^## \[([^\]]+)\]", re.MULTILINE)


def changelog_for_version(version: str) -> str:
    """Nur veröffentlichte Einträge bis einschließlich installierter Version."""
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    try:
        content = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    except OSError:
        return "Der lokale Versionsverlauf ist nicht verfügbar."
    sections = list(SECTION.finditer(content))
    selected = []
    installed = tuple(map(int, version.split(".")))
    for i, match in enumerate(sections):
        label = match.group(1)
        if not re.fullmatch(r"\d+\.\d+\.\d+", label):
            continue
        if tuple(map(int, label.split("."))) > installed:
            continue
        end = sections[i + 1].start() if i + 1 < len(sections) else len(content)
        selected.append(content[match.start():end].strip())
    if not selected:
        return "Für diese Version sind keine Einträge vorhanden."
    result = "\n\n".join(selected)
    result = re.sub(r"\*\*(.*?)\*\*", r"\1", result)
    result = re.sub(r"(?m)^###? ", "", result)
    result = re.sub(r"(?m)^- ", "• ", result)
    return result.replace("\x60", "")
