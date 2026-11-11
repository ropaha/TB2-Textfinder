"""Vergleich der Pfadmaskierung – ausschließlich Benchmark, keine Produktionsänderung.

Aufruf:
  py -3 benchmark_resource_paths.py "C:\\Signum\\TBL" --expected "C:\\Temp\\hagen.txt"

Liest TB2/TBL-Dateien nur. Vergleicht alte und experimentelle Maskierung
bytegenau sowie die Treffer der bestehenden JPEG-Schnellsuche nach "Hagen".
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from time import perf_counter

from tb2_resource_paths import _RESOURCE_PATH, _LEGACY_SERVER_PATH, mask_resource_paths
from tb2_jpeg_fast import contains_term_fast


def _mask(data: bytes, matches) -> bytes:
    spans = [(m.start(), m.end()) for m in matches]
    if not spans:
        return data
    result = bytearray(data)
    for start, end in spans:
        result[start:end] = b"\x00" * (end - start)
    return bytes(result)


def backslash_gate(data: bytes) -> bytes:
    """Sicherer Vorfilter: Beide bisherigen Muster verlangen Backslashes."""
    if b"\\" not in data:
        return data
    return mask_resource_paths(data)


def legacy_gate(data: bytes) -> bytes:
    """Alternative: Legacy-RegEx nur bei einem SYS-Pfad-Anker starten.

    ASCII-Großschreibung ist hier wichtig: die Original-RegEx nutzt IGNORECASE.
    Die vollständige Ressourcen-RegEx bleibt unverändert.
    """
    if b"\\" not in data:
        return data
    matches = list(_RESOURCE_PATH.finditer(data))
    if b"\\SYS\\" in data.upper():
        matches.extend(_LEGACY_SERVER_PATH.finditer(data))
    return _mask(data, matches)


CANDIDATES = {
    "original": mask_resource_paths,
    "backslash_gate": backslash_gate,
    "legacy_gate": legacy_gate,
}


def expected_paths(file: Path) -> set[str]:
    # Unterstützt kopierte Trefferlisten mit absoluten Pfaden, eine Zeile je Pfad.
    return {line.strip().strip('"').casefold() for line in file.read_text(
        encoding="utf-8-sig").splitlines() if line.strip()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path, help="Zu durchsuchender Ordner")
    parser.add_argument("--term", default="Hagen")
    parser.add_argument("--expected", type=Path, help="Gespeicherte Trefferpfade (TXT)")
    parser.add_argument("--output", type=Path, default=Path("benchmark_resource_paths.csv"))
    args = parser.parse_args()

    if not args.folder.is_dir():
        parser.error("Suchordner existiert nicht.")
    paths = sorted((p for p in args.folder.rglob("*")
                    if p.is_file() and p.suffix.lower() in (".tb2", ".tbl")),
                   key=lambda p: str(p).casefold())
    print(f"{len(paths)} Dateien; Begriff: {args.term!r}; Modus: Schnell")
    times = {name: 0.0 for name in CANDIDATES}
    search_times = {name: 0.0 for name in CANDIDATES}
    hits = {name: set() for name in CANDIDATES}
    differences = []
    errors = []
    started = perf_counter()

    for index, path in enumerate(paths, 1):
        try:
            data = path.read_bytes()
        except OSError as exc:
            errors.append((str(path), str(exc)))
            continue
        baseline = None
        for name, fn in CANDIDATES.items():
            start = perf_counter()
            masked = fn(data)
            times[name] += perf_counter() - start
            if name == "original":
                baseline = masked
            elif masked != baseline:
                differences.append((str(path), name))
            start = perf_counter()
            if contains_term_fast(masked, args.term, False):
                hits[name].add(str(path))
            search_times[name] += perf_counter() - start
        if index % 500 == 0:
            print(f"{index}/{len(paths)} verarbeitet ...", flush=True)

    reference = hits["original"]
    print(f"Gesamtzeit inkl. mehrfacher Suchen: {perf_counter()-started:.1f} s")
    for name in CANDIDATES:
        missing = reference - hits[name]
        extra = hits[name] - reference
        print(f"{name}: Maske {times[name]:.2f} s; Suche {search_times[name]:.2f} s;"
              f" Treffer {len(hits[name])}; fehlen {len(missing)}; zusätzlich {len(extra)}")
    print(f"Byteabweichungen zur Originalmaske: {len(differences)}")
    if args.expected:
        saved = expected_paths(args.expected)
        actual = {str(Path(p).resolve()).casefold() for p in reference}
        print(f"Gespeicherte Treffer: {len(saved)}; Originalsuche: {len(actual)}")
        print(f"Fehlende gespeicherte Pfade: {len(saved-actual)}")
        print(f"Zusätzliche Pfade: {len(actual-saved)}")
        for p in sorted(saved-actual):
            print("  FEHLT:", p)
        for p in sorted(actual-saved):
            print("  NEU:", p)
    with args.output.open("w", newline="", encoding="utf-8-sig") as out:
        writer = csv.writer(out, delimiter=";")
        writer.writerow(["Typ", "Variante", "Pfad", "Details"])
        for name, fn in CANDIDATES.items():
            writer.writerow(["Zeit_Maske_Sekunden", name, "", f"{times[name]:.6f}"])
            writer.writerow(["Zeit_Suche_Sekunden", name, "", f"{search_times[name]:.6f}"])
            for p in sorted(hits[name]):
                writer.writerow(["Treffer", name, p, ""])
        for p, name in differences:
            writer.writerow(["Maskenabweichung", name, p, ""])
        for p, err in errors:
            writer.writerow(["Lesefehler", "", p, err])
    print(f"CSV: {args.output}")
    return 1 if differences or any(hits[n] != reference for n in CANDIDATES) else 0


if __name__ == "__main__":
    raise SystemExit(main())
