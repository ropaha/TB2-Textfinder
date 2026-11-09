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
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be at least 1")
    files = sorted(p for p in args.folder.rglob("*") if p.is_file() and p.suffix.lower() in (".tb2", ".tbl"))
    print(f"Files: {len(files)}; term: {args.term!r}; repeats: {args.repeats}")
    print("file | size MB | JPEGs | JPEG MB | original ms | masked ms | preparation ms | same")
    mismatches = []
    for path in files:
        data = path.read_bytes()
        prep_ms, prepared = timed(lambda: (lambda spans: (spans, mask_jpegs(data, spans)))(jpeg_ranges(data)), args.repeats)
        spans, masked = prepared
        orig_ms, orig_hit = timed(lambda: contains_term(data, args.term), args.repeats)
        masked_ms, masked_hit = timed(lambda: contains_term(masked, args.term), args.repeats)
        same = orig_hit == masked_hit
        if not same:
            mismatches.append(str(path))
        print(f"{path.name} | {len(data)/1e6:.2f} | {len(spans)} | {sum(b-a for a,b in spans)/1e6:.2f} | "
              f"{orig_ms:.2f} | {masked_ms:.2f} | {prep_ms:.2f} | {same}")
    print(f"Result mismatches: {len(mismatches)}")
    for path in mismatches:
        print("WARNING: different search result:", path)
    print("Note: masked ms excludes JPEG detection and masking; compare with preparation ms added.")
    print("A matching result for one term does not prove that all search terms are safe.")


if __name__ == "__main__":
    main()
