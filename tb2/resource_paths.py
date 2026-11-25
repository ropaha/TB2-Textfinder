"""Maskiert eindeutig erkennbare eingebettete Ressourcen-/Dateipfade.

Nur Pfade mit mehreren Verzeichnisebenen und bekannten Dateiendungen
werden maskiert. Bytepositionen bleiben erhalten; Originaldateien
werden niemals veraendert.
"""
import re

_RESOURCE_PATH = re.compile(
    rb"\\+[A-Za-z0-9 _.-]+(?:\\[A-Za-z0-9 _.-]+){2,}"
    rb"\.(?:TB2|TBL|STNTN|STN|ORN|BAU|JPG|JPEG|BMP|PNG)(?![A-Za-z0-9])",
    re.IGNORECASE,
)

# Alte Signum-Pfade koennen ohne fuehrenden Backslash direkt an einen
# vorigen Ressourcennamen anschliessen (BENEKE.TB2: ...ORNHAGEN2\SYS\...).
# Nur die konkrete historische Verzeichnisstruktur wird akzeptiert.
_LEGACY_SERVER_PATH = re.compile(
    rb"[A-Za-z0-9_-]+\\SYS\\STEIN\\SIGNUM\\TBL\\[A-Za-z0-9 _.-]+\\[A-Za-z0-9 _.-]+",
    re.IGNORECASE,
)


def mask_resource_paths(data: bytes) -> bytes:
    # Historische Netzwerkpfade enthalten zwingend den Anker \\SYS\\.
    # Nur bei diesem Anker ist der zweite Regex-Durchlauf erforderlich.
    matches = list(_RESOURCE_PATH.finditer(data))
    if b"\\SYS\\" in data.upper():
        matches.extend(_LEGACY_SERVER_PATH.finditer(data))
    if not matches:
        return data
    masked = bytearray(data)
    for match in matches:
        masked[match.start():match.end()] = b"\x00" * (match.end() - match.start())
    return bytes(masked)


# Ressourcentypen: der Dateiname und die Endung sind entscheidend,
# niemals der Laufwerksbuchstabe oder die Verzeichnishierarchie.
RESOURCE_EXTENSIONS = {
    "FN2": "Schrift", "FN3": "Schrift", "FNT": "Schrift",
    "ORN": "Ornament", "BAU": "Baustein", "STN": "Stein",
    "ORNRN": "Ornament", "STNTN": "Stein",
}


def classify_resource_name(path: str):
    """(Typ, Name, Endung) oder None; Verzeichnisse werden ignoriert."""
    leaf = re.split(r"[\\/]", path)[-1]
    if "." not in leaf:
        return None
    name, ext = leaf.rsplit(".", 1)
    kind = RESOURCE_EXTENSIONS.get(ext.upper())
    if not name or kind is None:
        return None
    return kind, name, ext.upper()
