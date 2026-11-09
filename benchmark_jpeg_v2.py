"""JPEG-Benchmark v2: echte Bereichssuche und Profilanalyse (nur dev).

Aufruf: py -3 benchmark_jpeg_v2.py "C:\\Signum-Dateien" --term Gerken
Die Quelldateien werden nicht veraendert.
"""
import argparse
from collections import defaultdict
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


def searchable_regions(data, spans):
    """Gib unveraenderte, nicht-JPEG-Bereiche zurueck.

    Keine Verkettung: Zeichenabstaende duerfen nicht kuenstlich
    ueber JPEG-Grenzen hinweg entstehen.
    """
    previous = 0
    for start, end in spans:
        if start > previous:
            yield data[previous:start]
        previous = max(previous, end)
    if previous < len(data):
        yield data[previous:]


def search_regions(data, spans, term):
    return any(finder.contains_term(part, term) for part in searchable_regions(data, spans))


def profile_patterns(data, term):
    """Unabhaengige Messung aller Suchfamilien, ohne Kurzschluss."""
    checks = [("Klartext", lambda: any(data.find(n) >= 0 for n in finder._plain_needles(term, False)))]
    for name, marker, strides in finder.PROFILES:
        for stride in strides:
            offsets = (1, 7) if stride == 80 and marker == b"\x81\x00\x00" else ((7,) if stride == 98 else (1,))
            for offset in offsets:
                label = f"{name} / {stride} / offset {offset}"
                checks.append((label, lambda m=marker, s=stride, o=offset:
                               finder._matches_glyph_profile(data, term, m, s, False, o)))
    for label, func in (
        ("Variable 80", finder._matches_variable_80),
        ("Wide 587", finder._matches_wide_587),
        ("Early 80", finder._matches_early_80),
        ("Early 82", finder._matches_early_82),
        ("Variable 98", finder._matches_variable_98),
        ("Variable 106", finder._matches_variable_106),
        ("Legacy mixed", finder._matches_legacy_mixed_records),
    ):
        checks.append((label, lambda f=func: f(data, term, False)))
    results = []
    for label, check in checks:
        t = perf_counter()
        found = check()
        results.append((label, (perf_counter() - t) * 1000, found))
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--term", default="Gerken")
    parser.add_argument("--profile-limit", type=int, default=100,
                        help="Maximale Anzahl grosser Dateien fuer Musterprofiling (0 = aus)")
    args = parser.parse_args()
    if not args.folder.is_dir():
        parser.error("Ordner nicht gefunden")
    if args.profile_limit < 0:
        parser.error("--profile-limit muss >= 0 sein")

    files = sorted((p for p in args.folder.rglob("*")
                    if p.is_file() and p.suffix.lower() in (".tb2", ".tbl")),
                   key=lambda p: str(p))
    output = Path(__file__).resolve().parent / "benchmark_v2_ergebnis.txt"
    totals = defaultdict(float)
    profile = defaultdict(lambda: [0.0, 0, 0])
    mismatches = []
    errors = []
    count = 0
    images = image_bytes = bytes_total = 0
    profiled = 0
    t_all = perf_counter()
    interrupted = False

    with output.open("w", encoding="utf-8") as report:
        def log(message=""):
            report.write(message + "\n")
            report.flush()

        log("TB2 JPEG-Benchmark v2 | " + datetime.now().isoformat(timespec="seconds"))
        log(f"Ordner: {args.folder.resolve()} | Suchbegriff: {args.term}")
        log(f"Dateien: {len(files)} | Profil-Limit: {args.profile_limit}")
        log("Datei | MB | JPEGs | JPEG-MB | Original-ms | Bereich-ms | Erkennung-ms | Gleich")
        print(f"V2 startet: {len(files)} Dateien; Bericht: {output}", flush=True)
        try:
            for path in files:
                try:
                    data = path.read_bytes()
                    t = perf_counter()
                    baseline = finder.contains_term(data, args.term)
                    original_ms = (perf_counter() - t) * 1000

                    t = perf_counter()
                    spans = jpeg_ranges(data)
                    detect_ms = (perf_counter() - t) * 1000

                    t = perf_counter()
                    skipped = search_regions(data, spans, args.term)
                    region_ms = (perf_counter() - t) * 1000

                    # Profiling auf grossen Dateien mit JPEGs konzentrieren.
                    if spans and profiled < args.profile_limit:
                        for label, ms, hit in profile_patterns(data, args.term):
                            item = profile[label]
                            item[0] += ms
                            item[1] += 1
                            item[2] += int(hit)
                        profiled += 1
                except (OSError, ValueError, MemoryError) as exc:
                    errors.append((str(path), str(exc)))
                    continue
                count += 1
                bytes_total += len(data)
                images += len(spans)
                image_bytes += sum(end - start for start, end in spans)
                totals["original"] += original_ms
                totals["regions"] += region_ms
                totals["detect"] += detect_ms
                if baseline != skipped:
                    mismatches.append((str(path), baseline, skipped))
                log(f"{path} | {len(data)/1e6:.2f} | {len(spans)} | "
                    f"{sum(end-start for start,end in spans)/1e6:.2f} | "
                    f"{original_ms:.3f} | {region_ms:.3f} | {detect_ms:.3f} | "
                    f"{baseline == skipped}")
                if count % 100 == 0 or count == len(files):
                    print(f"Verarbeitet: {count}/{len(files)}", flush=True)
        except KeyboardInterrupt:
            interrupted = True
            print("Abgebrochen; Teilergebnisse werden gesichert.", flush=True)

        candidate = totals["regions"] + totals["detect"]
        saving = totals["original"] - candidate
        log("\n========== ZUSAMMENFASSUNG V2 ==========")
        log(f"Status: {'ABGEBROCHEN' if interrupted else 'Beendet'}")
        log(f"Dateien: {count}/{len(files)} | Fehler: {len(errors)}")
        log(f"Datenvolumen: {bytes_total/1e6:.2f} MB")
        log(f"JPEG-Bilder: {images} | JPEG-Volumen: {image_bytes/1e6:.2f} MB")
        log(f"Originalsuche: {totals['original']/1000:.3f} s")
        log(f"Echte Bereichssuche: {totals['regions']/1000:.3f} s")
        log(f"JPEG-Erkennung: {totals['detect']/1000:.3f} s")
        log(f"Bereichssuche + Erkennung: {candidate/1000:.3f} s")
        log(f"Ersparnis: {saving/1000:.3f} s ({100*saving/totals['original'] if totals['original'] else 0:.2f} %)")
        log(f"Abweichende Treffer: {len(mismatches)}")
        log(f"Tatsaechliche Testlaufzeit: {perf_counter()-t_all:.2f} s")
        log("\n========== MUSTER-PROFILING ==========")
        log(f"Unabhaengig getestet an {profiled} JPEG-Dateien; Profiling-Zeiten sind Zusatzaufwand.")
        log("Muster | Gesamt-ms | Dateien | Treffer")
        for label, (ms, tested, hits) in sorted(profile.items(), key=lambda kv: -kv[1][0]):
            log(f"{label} | {ms:.3f} | {tested} | {hits}")
        if mismatches:
            log("\nWARNUNG: ABWEICHENDE TREFFER")
            for path, original, regions in mismatches:
                log(f"{path} | original={original} | bereiche={regions}")
        if errors:
            log("\nFEHLER")
            for path, error in errors:
                log(f"{path}: {error}")
        log("\nACHTUNG: Bereichssuche ist nur ein Experiment. Glyphenfolgen, die")
        log("einen JPEG-Bereich ueberqueren, koennen uebersehen werden.")
        log("Gleiche Treffer fuer einen Begriff beweisen keine allgemeine Sicherheit.")
        log("Datei-Einlesezeit ist nicht in den Suchzeiten enthalten.")
    print(f"Original {totals['original']/1000:.2f}s | Bereiche+JPEG {candidate/1000:.2f}s")
    print(f"Ersparnis {saving/1000:.2f}s | Abweichungen {len(mismatches)} | Fehler {len(errors)}")
    print(f"Bericht: {output}", flush=True)


if __name__ == "__main__":
    main()
