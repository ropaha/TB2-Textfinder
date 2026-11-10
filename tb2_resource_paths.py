"""Maskiert eindeutig erkennbare eingebettete Ressourcen-/Dateipfade.

Nur Pfade mit mehreren Verzeichnisebenen und bekannten Dateiendungen
werden maskiert. Bytepositionen bleiben erhalten; Originaldateien
werden niemals veraendert.
"""
import re

_RESOURCE_PATH = re.compile(
    rb"\\+[A-Za-z0-9 _.-]+(?:\\[A-Za-z0-9 _.-]+){2,}"
    rb"\.(?:TB2|TBL|STNTN|STN|ORN|JPG|JPEG|BMP|PNG)(?![A-Za-z0-9])",
    re.IGNORECASE,
)


def mask_resource_paths(data: bytes) -> bytes:
    matches = list(_RESOURCE_PATH.finditer(data))
    if not matches:
        return data
    masked = bytearray(data)
    for match in matches:
        masked[match.start():match.end()] = b"\x00" * (match.end() - match.start())
    return bytes(masked)
