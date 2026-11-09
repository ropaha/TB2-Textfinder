"""TB2 JPEG Benchmark V3 - Multi-Term-Korrektheitstest (nur dev).

Beispiel:
    py -3 benchmark_jpeg_v3.py "C:\\Stein\\SignumNext\\TBL"

Liest Dateien nur, veraendert keine TB2/TBL-Dateien. V3 ist KEINE
freigegebene Produktionsoptimierung. Vergleich mit bestehender Suche.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path
from time import perf_counter

import TB2_Textfinder as finder

def jpeg_ranges(data: bytes) -> list[tuple[int, int]]:
    """Find structurally valid baseline/progressive JPEG streams.

    Parse marker segment lengths and entropy-coded scan data, including
    stuffed FF 00 and restart markers. Reject incomplete/invalid streams.
    """
    ranges = []
    cursor = 0
    while (start := data.find(b"\xff\xd8\xff", cursor)) != -1:
        pos = start + 2
        in_scan = False
        valid = True
        found_end = False
        while pos < len(data):
            if in_scan:
                next_ff = data.find(b"\xff", pos)
                if next_ff < 0:
                    valid = False
                    break
                pos = next_ff
                while pos < len(data) and data[pos] == 0xFF:
                    pos += 1
                if pos >= len(data):
                    valid = False
                    break
                marker = data[pos]
                if marker == 0x00 or 0xD0 <= marker <= 0xD7:
                    pos += 1
                    continue
                in_scan = False
            else:
                if data[pos] != 0xFF:
                    valid = False
                    break
                while pos < len(data) and data[pos] == 0xFF:
                    pos += 1
                if pos >= len(data):
                    valid = False
                    break
                marker = data[pos]
            pos += 1
            if marker == 0xD9:
                ranges.append((start, pos))
                found_end = True
                break
            if marker in (0xD8, 0x00) or 0xD0 <= marker <= 0xD7:
                valid = False
                break
            if pos + 2 > len(data):
                valid = False
                break
            length = int.from_bytes(data[pos:pos + 2], "big")
            if length < 2 or pos + length > len(data):
                valid = False
                break
            pos += length
            if marker == 0xDA:
                in_scan = True
        cursor = pos if valid and found_end else start + 3
    return ranges

# Bewusst unterschiedliche Schreibweisen, Laengen und Formatgenerationen.
DEFAULT_TERMS = (
    "Gerken", "Werner Gerken", "HEYCK", "Sindt", "Poetzing",
    "Pötzing", "Riebschläger", "Araxi", "Steen", "TEEGEN",
    "Fuchs", "Felicitas", "INGEBORG", "HANDELSHAUS",
    "Oma", "Gladebrügge", "Müller", "Schmidt",
    "A", "Stein", "Steinmetz", "Hans Peter",
    "ä", "Ö", "ß", "Straße", "2026",
    "XYZ_NICHT_VORHANDEN_987654321",
)


def outside_jpeg(data: bytes, spans: list[tuple[int, int]]):
    """Unveraenderte Teilbereiche; niemals ueber Bildgrenzen verbinden."""
    end = 0
    for start, stop in spans:
        if start > end:
            yield data[end:start]
        end = max(end, stop)
    if end < len(data):
        yield data[end:]


def search_without_jpeg(data: bytes, spans, term: str, case_sensitive: bool):
    # Ohne JPEG gibt es keinen Grund, Bytes zu kopieren.
    if not spans:
        return finder.contains_term(data, term, case_sensitive)
    return any(finder.contains_term(part, term, case_sensitive)
               for part in outside_jpeg(data, spans))


def terms_from_file(path: Path):
    return [line.strip() for line in path.read_text(encoding="utf-8-sig").splitlines()
            if line.strip() and not line.lstrip().startswith("#")]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path, help="TB2/TBL-Ordner")
    parser.add_argument("--terms-file", type=Path,
                        help="Optional: UTF-8-Datei mit einem Suchbegriff je Zeile")
    parser.add_argument("--term", action="append", default=[],
                        help="Zusaetzlicher Suchbegriff; mehrfach moeglich")
    parser.add_argument("--case-sensitive", action="store_true",
                        help="Gross-/Kleinschreibung beachten")
    parser.add_argument("--max-files", type=int, default=0,
                        help="0 = alle Dateien; sonst begrenzen fuer Kurztest")
    args = parser.parse_args()
    if not args.folder.is_dir():
        parser.error("Suchordner existiert nicht")
    if args.max_files < 0:
        parser.error("--max-files muss >= 0 sein")
    terms = list(DEFAULT_TERMS)
    if args.terms_file:
        try:
            terms.extend(terms_from_file(args.terms_file))
        except OSError as exc:
            parser.error(f"Begriffsdatei nicht lesbar: {exc}")
    terms.extend(args.term)
    terms = list(dict.fromkeys(term for term in terms if term))
    if not terms:
        parser.error("Keine Suchbegriffe")

    files = sorted((p for p in args.folder.rglob("*")
                    if p.is_file() and p.suffix.lower() in (".tb2", ".tbl")),
                   key=lambda p: str(p).casefold())
    if args.max_files:
        files = files[:args.max_files]
    directory = Path(__file__).resolve().parent
    report_path = directory / "benchmark_v3_ergebnis.txt"
    mismatch_path = directory / "benchmark_v3_abweichungen.csv"
    errors_path = directory / "benchmark_v3_fehler.csv"

    stats = {term: {"base": 0.0, "fast": 0.0, "hits_base": 0,
                    "hits_fast": 0, "diff": 0} for term in terms}
    count = 0
    error_count = 0
    mismatch_count = 0
    jpeg_count = 0
    jpeg_bytes = 0
    total_bytes = 0
    detect_seconds = 0.0
    read_seconds = 0.0
    start_all = perf_counter()
    interrupted = False
    print(f"V3: {len(files)} Dateien x {len(terms)} Suchbegriffe = "
          f"{len(files)*len(terms)} Vergleiche", flush=True)
    print(f"Ergebnis: {report_path}", flush=True)

    with (report_path.open("w", encoding="utf-8") as report,
          mismatch_path.open("w", encoding="utf-8-sig", newline="") as mismatch_file,
          errors_path.open("w", encoding="utf-8-sig", newline="") as errors_file):
        mismatch_writer = csv.writer(mismatch_file, delimiter=";")
        error_writer = csv.writer(errors_file, delimiter=";")
        mismatch_writer.writerow(["Datei", "Suchbegriff", "Original", "JPEG-Skip", "Gross-Klein"])
        error_writer.writerow(["Datei", "Fehler"])
        report.write("TB2 Benchmark V3 | " + datetime.now().isoformat(timespec="seconds") + "\n")
        report.write(f"Ordner: {args.folder.resolve()}\n")
        report.write(f"Dateien geplant: {len(files)} | Begriffe: {len(terms)}\n")
        report.write(f"Case-sensitive: {args.case_sensitive}\n")
        report.write("Suchbegriffe: " + " | ".join(terms) + "\n\n")
        report.flush()

        try:
            for path in files:
                try:
                    t = perf_counter()
                    data = path.read_bytes()
                    read_seconds += perf_counter() - t
                    t = perf_counter()
                    spans = jpeg_ranges(data)
                    detect_seconds += perf_counter() - t
                    # Erst erfolgreiche Datei als verarbeitet zaehlen.
                    count += 1
                    total_bytes += len(data)
                    jpeg_count += len(spans)
                    jpeg_bytes += sum(stop - begin for begin, stop in spans)
                    for term in terms:
                        t = perf_counter()
                        baseline = finder.contains_term(data, term, args.case_sensitive)
                        base_time = perf_counter() - t
                        t = perf_counter()
                        fast = search_without_jpeg(data, spans, term, args.case_sensitive)
                        fast_time = perf_counter() - t
                        item = stats[term]
                        item["base"] += base_time
                        item["fast"] += fast_time
                        item["hits_base"] += bool(baseline)
                        item["hits_fast"] += bool(fast)
                        if baseline != fast:
                            item["diff"] += 1
                            mismatch_count += 1
                            mismatch_writer.writerow([str(path), term, baseline, fast,
                                                      args.case_sensitive])
                            mismatch_file.flush()
                except (OSError, ValueError, MemoryError) as exc:
                    error_count += 1
                    error_writer.writerow([str(path), repr(exc)])
                    errors_file.flush()
                if (count + error_count) % 100 == 0:
                    print(f"V3: {count + error_count}/{len(files)} | "
                          f"Abweichungen: {mismatch_count}", flush=True)
        except KeyboardInterrupt:
            interrupted = True
            print("V3 abgebrochen; bisherige Ergebnisse werden gespeichert.", flush=True)

        base_total = sum(item["base"] for item in stats.values())
        fast_total = sum(item["fast"] for item in stats.values())
        # JPEG-Erkennung wird je Datei nur einmal ausgefuehrt, auch bei vielen Begriffen.
        candidate = fast_total + detect_seconds
        savings = base_total - candidate
        report.write("========== ZUSAMMENFASSUNG ==========\n")
        report.write(f"Status: {'ABGEBROCHEN' if interrupted else 'Beendet'}\n")
        report.write(f"Dateien verarbeitet: {count}/{len(files)}\n")
        report.write(f"Fehler: {error_count}\n")
        report.write(f"Suchbegriffe: {len(terms)}\n")
        report.write(f"Vergleiche: {sum(item['hits_base']*0 + count for item in stats.values())}\n")
        report.write(f"Dateivolumen: {total_bytes/1e6:.2f} MB\n")
        report.write(f"JPEGs: {jpeg_count} | JPEG-Bytes: {jpeg_bytes/1e6:.2f} MB\n")
        report.write(f"Originalsuche gesamt: {base_total:.3f} s\n")
        report.write(f"JPEG-Skip-Suche gesamt: {fast_total:.3f} s\n")
        report.write(f"JPEG-Erkennung einmal je Datei: {detect_seconds:.3f} s\n")
        report.write(f"JPEG-Skip + Erkennung: {candidate:.3f} s\n")
        report.write(f"Ersparnis: {savings:.3f} s "
                     f"({100*savings/base_total if base_total else 0:.2f} %)\n")
        report.write(f"Abweichende Ergebnisse: {mismatch_count}\n")
        report.write(f"Dateien lesen: {read_seconds:.3f} s\n")
        report.write(f"Echte Laufzeit inkl. Auswertung: {perf_counter()-start_all:.2f} s\n\n")
        report.write("========== JE SUCHBEGRIFF ==========\n")
        report.write("Begriff | Original-s | Skip-s | Originaltreffer | Skiptreffer | Abweichungen\n")
        for term, item in stats.items():
            report.write(f"{term} | {item['base']:.3f} | {item['fast']:.3f} | "
                         f"{item['hits_base']} | {item['hits_fast']} | {item['diff']}\n")
        report.write("\nHINWEISE:\n")
        report.write("- Gleiche Treffer fuer diese Begriffe beweisen keine universelle Sicherheit.\n")
        report.write("- Ein Glyphenmuster kann ueber eine JPEG-Grenze reichen.\n")
        report.write("- Die Summen sind gemessene Suchzeiten, kein Ende-zu-Ende-Benchmark.\n")
        report.write("- JPEG-Erkennung wird bei diesem Multi-Term-Test einmal je Datei berechnet.\n")
        report.write("- Dateiinhalte wurden nicht veraendert.\n")

    print(f"Fertig: {count} Dateien, {len(terms)} Begriffe, "
          f"{mismatch_count} Abweichungen, {error_count} Fehler.", flush=True)
    print(f"Original: {base_total:.2f}s | JPEG-Skip inkl. Erkennung: "
          f"{candidate:.2f}s | Ersparnis: {savings:.2f}s", flush=True)
    print(f"Bericht: {report_path}", flush=True)
    print(f"Abweichungen: {mismatch_path}", flush=True)


if __name__ == "__main__":
    main()
