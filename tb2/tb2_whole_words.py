"""Experimentelle Ganzwortsuche in Klartext und bekannten TB2-Glyphenprofilen."""
from __future__ import annotations
import re

PROFILES = (
    (106, "a"), (106, "b"), (80, "a"), (80, "a7"),
    (98, "a7"), (80, "early"), (80, "v80"), (80, "e80"),
    (80, "e82"), (98, "v98"), (106, "v106"), (587, "wide"),
)

def _record(data: bytes, p: int, kind: str) -> bool:
    if p < 0 or p + 10 > len(data):
        return False
    if kind == "a": return data[p+1:p+4] == b"\x81\x00\x00"
    if kind == "b": return data[p+1:p+8] == b"\x81\x67\x66\x66\x66\x66\x81"
    if kind == "a7": return data[p+7:p+10] == b"\x81\x00\x00"
    if kind == "early": return data[p+1:p+7] == b"\x81\x7c\xe9\xe4\x58\x09"
    if kind == "v80": return data[p+1] == 0x81 and data[p+7] in (0x80, 0x81)
    if kind == "e80": return data[p+1] == 0x80 and data[p+7] in (0x80, 0x81)
    if kind == "e82": return data[p+1] == 0x82 and data[p+7] in (0x80, 0x81)
    if kind == "v98": return data[p+1] in (0x80, 0x81) and data[p+7] in (0x80, 0x81)
    if kind == "v106": return data[p+1] in (0x81, 0x82) and data[p+7:p+10] == b"\x81\x00\x00"
    if kind == "wide": return data[p+1] in (0x7e, 0x7f, 0x80, 0x81, 0x84) and data[p+7] in (0x80, 0x81)
    return False

def _word_byte(value: int) -> bool:
    # Bei OEM- und ANSI-Codepages sind Buchstaben ab 0x80 unterschiedlich
    # belegt. Lieber einen fraglichen Nachbarn als Wortbestandteil behandeln.
    if value in (0x20, 0xfa, 0x2d): return False
    for encoding in ("cp850", "cp437", "cp1252", "latin-1"):
        char = bytes((value,)).decode(encoding, errors="replace")
        if char.isalnum() or char == "_":
            return True
    return False

def _glyph_match(data: bytes, term: str, case_sensitive: bool) -> bool:
    from TB2_Textfinder import _glyph_char_codes
    codes = [_glyph_char_codes(ch, case_sensitive) for ch in term]
    if not codes or any(not c for c in codes): return False
    for stride, kind in PROFILES:
        for first in codes[0]:
            needle = bytes((first,))
            start = data.find(needle)
            while start >= 0:
                end = start + (len(term)-1)*stride
                if (end + 10 <= len(data) and
                    all(data[start+i*stride] in allowed and
                        _record(data, start+i*stride, kind)
                        for i, allowed in enumerate(codes))):
                    left, right = start-stride, end+stride
                    if not (left >= 0 and _record(data, left, kind) and _word_byte(data[left])) and not (
                        right+10 <= len(data) and _record(data, right, kind) and _word_byte(data[right])):
                        return True
                start = data.find(needle, start+1)
    return False

def _plain_match(data: bytes, term: str, case_sensitive: bool) -> bool:
    pattern = re.compile(r"(?<!\w)" + re.escape(term) + r"(?!\w)",
                         0 if case_sensitive else re.IGNORECASE)
    # UTF-16 nur bei nachweisbarem UTF-16-Muster; andernfalls können
    # die NUL-Bytes künstliche Wortgrenzen vortäuschen.
    encodings = ("utf-8", "cp850", "cp1252", "latin-1")
    if b"\x00" in data: encodings += ("utf-16le",)
    for encoding in encodings:
        if pattern.search(data.decode(encoding, errors="replace")):
            return True
    return False

def contains_whole_word(data: bytes, term: str, case_sensitive: bool = False) -> bool:
    return bool(term) and (_plain_match(data, term, case_sensitive) or
                           _glyph_match(data, term, case_sensitive))
