"""Experimentelle JPEG-Skip-Suche fuer TB2-Textfinder (dev).

Originaldateien werden ausschliesslich gelesen. Die Suchroutine nutzt
dieselbe JPEG-Erkennung wie Benchmark V3.
"""
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

def contains_term_fast(data: bytes, term: str, case_sensitive: bool = False) -> bool:
    spans = jpeg_ranges(data)
    if not spans:
        return contains_term(data, term, case_sensitive)
    previous = 0
    for start, end in spans:
        if start > previous and contains_term(data[previous:start], term, case_sensitive):
            return True
        previous = max(previous, end)
    return previous < len(data) and contains_term(data[previous:], term, case_sensitive)
