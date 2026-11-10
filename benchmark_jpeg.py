"""Experimental benchmark: search original TB2 data vs JPEG-masked data.

Run: py -3 benchmark_jpeg.py "C:\\Signum-Dateien" --term Gerken
No source files are modified. This is NOT a production optimization.
"""
import argparse
from pathlib import Path
from statistics import median
from time import perf_counter

from TB2_Textfinder import contains_term


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


def mask_jpegs(data: bytes, ranges: list[tuple[int, int]]) -> bytes:
    """Preserve offsets/strides; zero only confirmed JPEG payload bytes."""
    masked = bytearray(data)
    for start, end in ranges:
        masked[start:end] = b"\x00" * (end - start)
    return bytes(masked)


def timed(fn, repeats: int) -> tuple[float, object]:
    times = []
    result = None
    for _ in range(repeats):
        t0 = perf_counter()
        result = fn()
        times.append((perf_counter() - t0) * 1000)
    return median(times), result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--term", default="Gerken")
    parser.add_argument("--repeats", type=int, default=1)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be at least 1")
    if not args.folder.is_dir():
        parser.error(f"Folder not found: {args.folder}")

    from datetime import datetime
    import sys

    output = Path(__file__).resolve().parent / "benchmark_ergebnis.txt"
    files = sorted(p for p in args.folder.rglob("*")
                   if p.is_file() and p.suffix.lower() in (".tb2", ".tbl"))
    total = len(files)
    count = images = image_bytes = file_bytes = 0
    orig_total = masked_total = prep_total = 0.0
    mismatches = []
    errors = []
    start_time = perf_counter()

    with output.open("w", encoding="utf-8") as report:
        def write(line=""):
            report.write(line + "\n")
            report.flush()

        write("TB2-Textfinder: JPEG-Benchmark")
        write(f"Datum: {datetime.now():%Y-%m-%d %H:%M:%S}")
        write(f"Ordner: {args.folder.resolve()}")
        write(f"Suchbegriff: {args.term}")
        write(f"Wiederholungen pro Messung: {args.repeats}")
        write(f"Gefundene TB2/TBL-Dateien: {total}")
        write()
        write("Einzelergebnisse: Datei | MB | JPEGs | JPEG-MB | Original-ms | Maskiert-ms | Vorbereitung-ms | Gleich")
        print(f"Benchmark gestartet: {total} Dateien; Bericht: {output}", flush=True)

        try:
            for path in files:
                try:
                    data = path.read_bytes()
                    prep_ms, prepared = timed(
                        lambda: (lambda spans: (spans, mask_jpegs(data, spans)))(
                            jpeg_ranges(data)), args.repeats)
                    spans, masked = prepared
                    orig_ms, orig_hit = timed(
                        lambda: contains_term(data, args.term), args.repeats)
                    masked_ms, masked_hit = timed(
                        lambda: contains_term(masked, args.term), args.repeats)
                except (OSError, ValueError, MemoryError) as exc:
                    errors.append((str(path), str(exc)))
                    continue

                count += 1
                file_bytes += len(data)
                images += len(spans)
                image_bytes += sum(end - begin for begin, end in spans)
                orig_total += orig_ms
                masked_total += masked_ms
                prep_total += prep_ms
                if orig_hit != masked_hit:
                    mismatches.append(str(path))
                write(f"{path} | {len(data)/1e6:.2f} | {len(spans)} | "
                      f"{sum(end-begin for begin,end in spans)/1e6:.2f} | "
                      f"{orig_ms:.2f} | {masked_ms:.2f} | {prep_ms:.2f} | "
                      f"{orig_hit == masked_hit}")
                if count % 100 == 0 or count == total:
                    print(f"Verarbeitet: {count}/{total} Dateien", flush=True)
        except KeyboardInterrupt:
            print("\nAbgebrochen; bisherige Ergebnisse werden gespeichert.", flush=True)
            write("\nWARNUNG: Test vorzeitig abgebrochen.")

        candidate_total = masked_total + prep_total
        saving = orig_total - candidate_total
        write()
        write("========== ZUSAMMENFASSUNG ==========")
        write(f"Dateien insgesamt:                 {total}")
        write(f"Erfolgreich verarbeitet:           {count}")
        write(f"Lesefehler / andere Fehler:        {len(errors)}")
        write(f"Gesamtgroesse Dateien:             {file_bytes/1e6:.2f} MB")
        write(f"Erkannte JPEG-Bilder:              {images}")
        write(f"Gesamtgroesse JPEG-Bloecke:        {image_bytes/1e6:.2f} MB")
        write(f"Bisherige Suche:                   {orig_total/1000:.3f} s")
        write(f"Suche mit maskierten Bildern:      {masked_total/1000:.3f} s")
        write(f"JPEG-Erkennung und Vorbereitung:   {prep_total/1000:.3f} s")
        write(f"Neue Gesamtzeit (geschaetzt):      {candidate_total/1000:.3f} s")
        write(f"Moegliche Zeitersparnis:           {saving/1000:.3f} s")
        write(f"Zeitersparnis in Prozent:          {(saving/orig_total*100) if orig_total else 0:.2f} %")
        write(f"Abweichende Suchergebnisse:        {len(mismatches)}")
        write(f"Tatsaechliche Benchmark-Laufzeit:  {perf_counter()-start_time:.2f} s")
        if mismatches:
            write("\nAbweichungen:")
            for item in mismatches:
                write(item)
        if errors:
            write("\nFehler:")
            for item, reason in errors:
                write(f"{item}: {reason}")
        write()
        write("Hinweis: Summierte Median-Messzeiten; keine echte Ende-zu-Ende-Laufzeit.")
        write("Maskieren ist kein physisches Ueberspringen von JPEG-Bloecken.")
        write("Gleiche Treffer fuer einen Begriff garantieren keine allgemeine Sicherheit.")

    print("\n========== ZUSAMMENFASSUNG ==========")
    print(f"Dateien: {count}/{total}; JPEGs: {images} ({image_bytes/1e6:.2f} MB)")
    print(f"Bisherige Suche: {orig_total/1000:.3f} s")
    print(f"Maskierte Suche + Vorbereitung: {candidate_total/1000:.3f} s")
    print(f"Moegliche Ersparnis: {saving/1000:.3f} s "
          f"({(saving/orig_total*100) if orig_total else 0:.2f} %)")
    print(f"Abweichende Treffer: {len(mismatches)}; Fehler: {len(errors)}")
    print(f"Bericht gespeichert: {output}", flush=True)


if __name__ == "__main__":
    main()
