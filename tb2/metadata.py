"""Conservative, read-only Signum document header metadata."""
import re
from collections import Counter

def extract_metadata(data):
    result = dict(file_version=None, format=None, created_exe_version=None,
                  created_exe_name=None)
    if len(data) < 4:
        return result
    version = int.from_bytes(data[:4], "little")
    if version >> 16 != 0xABCD:
        return result
    result["file_version"] = f"{version:08X}"
    if version != 0xABCD1114:
        return result
    pos = 4
    values = []
    for pattern in (rb"[0-9]+(?:\.[0-9]+){1,3}", rb"[A-Za-z0-9_. -]+\.[Ee][Xx][Ee]"):
        if pos + 4 > len(data):
            return result
        length = int.from_bytes(data[pos:pos+4], "little")
        pos += 4
        if not 1 <= length <= 128 or pos + length > len(data):
            return result
        raw = data[pos:pos+length]
        if not re.fullmatch(pattern, raw):
            return result
        values.append(raw.decode("ascii"))
        pos += length
    result["created_exe_version"], result["created_exe_name"] = values
    return result

def summarize_metadata(rows):
    groups = {}
    for row in rows:
        meta = row.get("metadata") or {}
        version = meta.get("file_version") or "Unbekannt"
        group = groups.setdefault(version, {"files": 0, "statuses": Counter(), "created_exe_versions": Counter()})
        group["files"] += 1
        group["statuses"][row.get("status", "Unbekannt")] += 1
        group["created_exe_versions"][meta.get("created_exe_version") or "Unbekannt"] += 1
    return groups
