"""Gemeinsame empirische TB2-Glyphenprofile und Byte-Suchhilfe."""

PROFILES = (
    # Neue und mittlere Generation: Zeichen + Marker, Abstand 106 Bytes.
    ("SignumNext-Profil A", b"\x81\x00\x00", (0x6A,)),
    ("SignumNext-Profil B", b"\x81\x67\x66\x66\x66\x66\x81", (0x6A,)),
    # Ältere Generation (z. B. Datei 9500036.TB2, Jahrgang 1995):
    # gleicher Zeichenmarker, aber nur 80 Bytes Abstand.
    ("Signum-Altformat", b"\x81\x00\x00", (0x50,)),
    # Sehr frühe Generation (z. B. 8900001.TB2):
    # eigener Marker direkt hinter jedem Zeichen; ebenfalls 80 Bytes Abstand.
    ("Signum-Frühformat", b"\x81\x7C\xE9\xE4\x58\x09", (0x50,)),
    # 1990–1993: 98-Byte-Datensaetze, variabler 6-Byte-Vorspann
    # zwischen Zeichen und festem Marker 81 00 00.
    ("Signum-90er-Profil", b"\x81\x00\x00", (0x62,)),
)


def find_all(data: bytes, needle: bytes):
    start = 0
    while True:
        pos = data.find(needle, start)
        if pos < 0:
            return
        yield pos
        start = pos + 1


def _variable_marker_record(data: bytes, pos: int) -> bool:
    """Ältere 80-Byte-Glyphen: variable 5-Byte-Felder nach 0x81.

    Beobachtet bei 9005016.TB2. Das Folgesteuerbyte an +7 ist
    0x80 oder 0x81. Diese Struktur vermeidet blindes Stride-Matching.
    """
    return (pos >= 0 and pos + 8 <= len(data)
            and data[pos + 1] == 0x81
            and data[pos + 7] in (0x80, 0x81))



def _early_80_record(data: bytes, pos: int) -> bool:
    """Frühes 80-Byte-Profil mit 0x80 direkt nach dem Zeichen.

    Beobachtet in 9518311I.TB2 (Kl.Gladebrügge). Die 5 variablen
    Steuerbytes werden nicht als feste Signatur interpretiert.
    """
    return (0 <= pos and pos + 8 <= len(data)
            and data[pos + 1] == 0x80
            and data[pos + 7] in (0x80, 0x81))



def has_early_80_pattern(data: bytes, minimum: int = 3) -> bool:
    minimum = max(3, minimum)
    for marker_pos in find_all(data, b"\x80"):
        start = marker_pos - 1
        if start < 0 or start + (minimum - 1) * 80 + 8 > len(data):
            continue
        if all(_early_80_record(data, start + i * 80)
               and (32 <= data[start + i * 80] <= 126
                    or data[start + i * 80] >= 0x80)
               for i in range(minimum)):
            return True
    return False



def has_variable_80_pattern(data: bytes, minimum: int = 3) -> bool:
    """Mindestens drei plausible Datensätze mit variablem Marker."""
    if minimum < 3:
        minimum = 3
    for marker_pos in find_all(data, b"\x81"):
        start = marker_pos - 1
        if start < 0:
            continue
        if all(_variable_marker_record(data, start + i * 80)
               and (32 <= data[start + i * 80] <= 126
                    or data[start + i * 80] >= 0x80)
               for i in range(minimum)
               if start + i * 80 < len(data)):
            if start + (minimum - 1) * 80 + 8 <= len(data):
                return True
    return False


def _wide_587_record(data: bytes, pos: int) -> bool:
    """587-Byte-Glyphen mit beobachteten Steuerbytes 7E/7F/80/81/84."""
    return (0 <= pos and pos + 8 <= len(data)
            and data[pos + 1] in (0x7E, 0x7F, 0x80, 0x81, 0x84)
            and data[pos + 7] in (0x80, 0x81))



def has_wide_587_pattern(data: bytes, minimum: int = 3) -> bool:
    """Mindestens drei aufeinanderfolgende plausible 587-Byte-Zeichen."""
    minimum = max(3, minimum)
    for marker in (b"\x7e", b"\x7f", b"\x80", b"\x81", b"\x84"):
        for marker_pos in find_all(data, marker):
            start = marker_pos - 1
            if start < 0 or start + (minimum - 1) * 587 + 8 > len(data):
                continue
            if all(_wide_587_record(data, start + i * 587)
                   and (32 <= data[start + i * 587] <= 126
                        or data[start + i * 587] >= 0x80)
                   for i in range(minimum)):
                return True
    return False





def _early_82_record(data: bytes, pos: int) -> bool:
    """80-Byte-Zeichendatensatz mit 0x82 nach dem Zeichen.

    Referenz: 9600246.TB2 (HANDELSHAUS). Der Vorspann an +2..+6
    kann variieren; +7 ist bei diesem Datensatz 0x80 oder 0x81.
    """
    return (0 <= pos and pos + 8 <= len(data)
            and data[pos + 1] == 0x82
            and data[pos + 7] in (0x80, 0x81))



def has_early_82_pattern(data: bytes, minimum: int = 3) -> bool:
    minimum = max(3, minimum)
    for marker_pos in find_all(data, b"\x82"):
        start = marker_pos - 1
        if start < 0 or start + (minimum - 1) * 80 + 8 > len(data):
            continue
        if all(_early_82_record(data, start + i * 80)
               and (32 <= data[start + i * 80] <= 126
                    or data[start + i * 80] >= 0x80)
               for i in range(minimum)):
            return True
    return False




def _variable_98_record(data: bytes, pos: int) -> bool:
    """98-Byte-Zeichen: variables Steuerfeld und 0x80/0x81 an Position +7.

    Referenz 2006 18 178d.TB2 (1923 INGEBORG 2006).
    Erfordert 0x80/0x81 an +1 und 0x80/0x81 an +7; kein blindes Stride-Matching.
    """
    return (0 <= pos and pos + 8 <= len(data)
            and data[pos + 1] in (0x80, 0x81)
            and data[pos + 7] in (0x80, 0x81))



def has_variable_98_pattern(data: bytes, minimum: int = 3) -> bool:
    minimum = max(3, minimum)
    for marker in (b"\x80", b"\x81"):
        for marker_pos in find_all(data, marker):
            start = marker_pos - 1
            if start < 0 or start + (minimum - 1) * 98 + 8 > len(data):
                continue
            if all(_variable_98_record(data, start + i * 98)
                   and (32 <= data[start + i * 98] <= 126
                        or data[start + i * 98] >= 0x80)
                   for i in range(minimum)):
                return True
    return False


def _variable_106_record(data: bytes, pos: int) -> bool:
    """106-Byte-Glyphen mit variablen Steuerdaten.

    Referenzen: 2018-00-149.TB2 (Fuchs) und 2020-01-012.TB2
    (Oma, Felicitas). Das Steuerbyte an +1 darf 0x81 oder 0x82
    sein; die 5 folgenden Bytes sind variabel. Die beobachtete
    Abschlussstruktur +7..+9 bleibt verpflichtend.
    """
    return (0 <= pos and pos + 10 <= len(data)
            and data[pos + 1] in (0x81, 0x82)
            and data[pos + 7:pos + 10] == b"\x81\x00\x00")



def has_variable_106_pattern(data: bytes, minimum: int = 3) -> bool:
    minimum = max(3, minimum)
    for marker in (b"\x81", b"\x82"):
        for marker_pos in find_all(data, marker):
            start = marker_pos - 1
            if start < 0 or start + (minimum - 1) * 106 + 10 > len(data):
                continue
            if all(_variable_106_record(data, start + i * 106)
                   and (32 <= data[start + i * 106] <= 126
                        or data[start + i * 106] >= 0x80)
                   for i in range(minimum)):
                return True
    return False





# Textcounter: strukturell bestaetigte Schrift-Eintraege.
import re
from tb2_resource_paths import classify_resource_name

_COUNTER_FONT = re.compile(rb"Signum Standard\\([A-Za-z0-9_. -]{1,64})")
_LEGACY_TEXT = re.compile(rb"[A-Za-z0-9_ .\\/-]+")


def _eva2p12_glyph(data, q):
    g = data[q:q+10]
    return (len(g) == 10 and (32 <= g[0] <= 126 or g[0] >= 128)
            and g[1] in (0x83, 0x84)
            and (g[7:] == b'\x81\x00\x00'
                 or (g[0] == 46 and g[7:] == b'\x81\x49\x92')))


def _grotesk1_number_glyph(data, q):
    return (q + 10 <= len(data) and 48 <= data[q] <= 57
            and data[q + 1] == 0x7C
            and data[q + 7:q + 10] == b"\x81\x00\x00")


def _counter_font_entries(data: bytes):
    """(Position, Schrift, erster Glyphenoffset, Abstand, Altformat).

    Die historischen Felder beginnen mit einem Laengenbyte. Ein Dateipfad
    ist optional; Ressourcen mit Nicht-Schrift-Endung sind ausgeschlossen.
    """
    entries = []
    for match in _COUNTER_FONT.finditer(data):
        pos = match.start() + 343
        # Ressourcen-Strings in eingebetteten Daten sind keine Textzeilen.
        # Nur Kandidaten mit mindestens zwei echten Glyphen uebernehmen.
        if (pos + 116 <= len(data)
                and all(data[q + 1] in (0x7E, 0x80, 0x81, 0x82)
                        and data[q + 7:q + 10] == b"\x81\x00\x00"
                        for q in (pos, pos + 106))):
            entries.append((match.start(), match.group(1).decode("ascii"),
                            pos, 106, False))

    # EVA2NEU V1.1 (Referenz: 2008 00 035.TB2): 98-Byte-Glyphen
    # mit Steuerbyte 0x7D und festem Abschlussmarker. Der Schriftname
    # besitzt ein Laengenbyte und darf Leerzeichen/Punkte enthalten.
    # Nur mit zwei aufeinanderfolgenden strukturell gueltigen Glyphen.
    for match in re.finditer(rb"\x0cEVA2NEU V1\.1", data):
        start = match.start() + 1
        pos = start + 343
        if (pos + 108 <= len(data)
                and all(data[q + 1] in (0x7D, 0x80, 0x81)
                        and data[q + 7:q + 10] == b"\x81\x00\x00"
                        for q in (pos, pos + 98))):
            entries.append((start, "EVA2NEU V1.1", pos, 98, False))

    # Bei den alten Formaten kommt der Glyphenbeginn je nach Feldlayout
    # nach 98 oder 105 Bytes. Nur durch zwei gueltige Glyphen bestaetigen.
    for start in range(1, len(data)):
        length = data[start - 1]
        if not (3 <= length <= 90 and start + length <= len(data)
                and 65 <= data[start] <= 122):
            continue
        raw = data[start:start + length]
        if _LEGACY_TEXT.fullmatch(raw) is None:
            continue
        value = raw.decode("ascii")
        if raw == b"GROTESK1":
            pos = start + 343
            if (pos + 206 <= len(data) and data[start + 285] == 3
                    and all(_grotesk1_number_glyph(data, pos + k * 98) for k in range(3))):
                entries = [e for e in entries if e[0] != start]
                entries.append((start, "GROTESK1", pos, 98, "grotesk1_number"))
                continue
        if value == "ABLAGE\\EVA2P12" and start + 343 <= len(data):
            pos = start + 343
            count = data[start + 285]
            if (count and pos + (count - 1) * 80 + 10 <= len(data)
                    and all(_eva2p12_glyph(data, pos + k * 80) for k in range(count))):
                entries = [e for e in entries if e[0] != start]
                entries.append((start, "EVA2P12", pos, 80, "eva2p12"))
                continue
        # Historisches 587-Byte-Raster (z.B. GROTESK1, GROTESK3,
        # EVA2NEU V1.1): kein Schluss vom Schriftnamen auf den Stride.
        # Die gespeicherte Zeilenlaenge bei +285 und *alle* Glyphen
        # muessen die erwartete Struktur bestaetigen.
        wide_font = value[7:] if value.upper().startswith("ABLAGE\\") else value
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9_. -]{2,40}", wide_font):
            pos = start + 343
            if start + 285 < len(data):
                count = data[start + 285]
                if (2 <= count <= 255
                        and pos + (count - 1) * 587 + 10 <= len(data)
                        and all(_wide_587_record(data, pos + k * 587)
                                and (32 <= data[pos + k * 587] <= 126
                                     or data[pos + k * 587] >= 0x80)
                                for k in range(count))):
                    entries = [e for e in entries if e[0] != start]
                    entries.append((start, wide_font, pos, 587, True))
                    continue
        resource = classify_resource_name(value)
        leaf = re.split(r"[\\/]", value)[-1]
        if "." in leaf and resource is None:
            continue
        if resource is not None:
            kind, font, _extension = resource
            if kind != "Schrift":
                continue
        else:
            font = leaf
        # SignumNext kann auch einen laengenpraefigierten Schriftnamen
        # ohne "Signum Standard"-Pfad verwenden (z.B. GROTESK3D BT).
        modern_pos = start + 343
        if (modern_pos + 116 <= len(data)
                and all(data[q + 1] in (0x7E, 0x80, 0x81, 0x82)
                        and data[q + 7:q + 10] == b"\x81\x00\x00"
                        for q in (modern_pos, modern_pos + 106))):
            modern_font = re.sub(r"D BT$", "", leaf).strip()
            if re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{2,30}", modern_font):
                entries.append((start, modern_font, modern_pos, 106, False))
                continue
        # Altformat mit 98-Byte-Glyphen und 343-Byte-Vorspann,
        # bestaetigt an 9000009.TB2 (1990).
        if (modern_pos + 108 <= len(data)
                and all(data[q + 1] in (0x7D, 0x7F, 0x80, 0x81, 0x82)
                        and data[q + 7:q + 10] == b"\x81\x00\x00"
                        for q in (modern_pos, modern_pos + 98))):
            if re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{2,30}", font):
                entries.append((start, font, modern_pos, 98, False))
                continue
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{2,30}", font) is None:
            continue
        if font.endswith("SK"):
            font = font[:-2]
        if font.endswith("i") and font[:-1].upper().startswith("GROTESK"):
            font = font[:-1]
        for offset in (98, 105, 343):
            pos = start + offset
            if pos + 88 > len(data):
                continue
            if all((data[q + 1] in (0x80, 0x81, 0x82)
                    and data[q + 7] in (0x80, 0x81))
                   or (data[q + 1] in (0x7E, 0x7F)
                       and data[q + 7] == 0x81)
                   
                   for q in (pos, pos + 80)):
                entries.append((start, font, pos, 80, True))
                break
    # Derselbe Schriftsatz kann sowohl vom Pfad- als auch vom
    # Laengenfeld-Detektor erkannt werden. Doppelte Eintraege haben
    # sonst dieselbe Startposition und erzeugen durch die Grenzbildung
    # eine falsche Warnung (beobachtet bei Eva4 im Jahrgang 2025).
    entries.sort(key=lambda entry: entry[0])
    unique = []
    seen = set()
    for entry in entries:
        signature = (entry[0], entry[2], entry[3], entry[4])
        if signature not in seen:
            seen.add(signature)
            unique.append(entry)
    # Embedded header strings can align with later glyphs of a real line.
    # Suppress only zero-count candidates aligned within a fully validated
    # 80/98-byte line with the same header layout.
    filtered = []
    for entry in unique:
        start, font, pos, stride, legacy = entry
        if (stride in (80, 98) and pos == start + 343
                and data[start + 285] == 0):
            overlap = False
            for s, f, p, t, l in reversed(filtered):
                if t != stride or l != legacy or p != s + 343:
                    continue
                count = data[s + 285]
                delta = start - s
                if not (2 <= count <= 255 and 0 < delta < count * t
                        and delta % t == 0 and p + (count - 1) * t + 10 <= len(data)):
                    continue
                def valid(q):
                    if not (32 <= data[q] <= 126 or data[q] >= 128):
                        return False
                    if l:
                        return ((data[q + 1] in (0x80, 0x81, 0x82) and data[q + 7] in (0x80, 0x81))
                                or (data[q + 1] in (0x7E, 0x7F) and data[q + 7] == 0x81))
                    return (data[q + 1] in (0x7D, 0x7F, 0x80, 0x81, 0x82)
                            and data[q + 7:q + 10] == b"\x81\x00\x00")
                if all(valid(p + k * t) for k in range(count)):
                    overlap = True
                    break
            if overlap:
                continue
        filtered.append(entry)
    return filtered


def historical_resource_339(data):
    if len(data) < 375 or data[:4] not in (b'\x00\x05\xcd\xab', b'\x25\x07\xcd\xab'):
        return None
    count = data[35]
    if not count or len(data) != 36 + count * 339:
        return None
    types = {1: 'STN', 2: 'ORN', 3: 'BAU'}
    result = []
    for p in range(36, len(data), 339):
        ext = types.get(data[p+40])
        n = data[p+57]
        if ext is None or data[p+41:p+57] != bytes(16) or not 5 <= n <= 56:
            return None
        path = data[p+58:p+58+n].decode('latin-1').upper()
        prefix = 'F:\\STEIN\\SIGNUM\\' + ext + '\\'
        if not path.startswith(prefix) or not re.fullmatch(r'(?:[A-ZÄÖÜ0-9_ .-]+\\)*[A-ZÄÖÜ0-9_ .-]+\.' + ext, path[len(prefix):]):
            return None
        result.append(ext)
    return tuple(result)


def historical_resource_document(data):
    """Return resource types for a fully matched historical document, else None."""
    if data[:4] in (b'\x00\x05\xcd\xab', b'\x25\x07\xcd\xab'):
        return historical_resource_339(data)
    if len(data) < 150 or data[:4] != bytes.fromhex('5003cdab'):
        return None
    count = data[35]
    if not count or len(data) != 36 + count * 114:
        return None
    types = {1: b'STN', 2: b'ORN', 3: b'BAU'}
    result = []
    for p in range(36, len(data), 114):
        ext = types.get(data[p+40])
        n = data[p+57]
        if ext is None or data[p+41:p+57] != bytes(16) or not 5 <= n <= 56:
            return None
        path = data[p+58:p+58+n].upper()
        if not re.fullmatch(rb'[A-Z0-9_ .\\-]+\.' + ext, path) or not path.startswith(ext + b'\\'):
            return None
        result.append(ext.decode('ascii'))
    return tuple(result)


def extract_counter_lines(data: bytes):
    """Liefert ([(Schriftsatz, Glyphenbytes)], Warnungen)."""
    if historical_resource_document(data) is not None:
        return [], []
    entries = _counter_font_entries(data)
    lines = []
    warnings = []
    if not entries:
        warnings.append(
            "Kein bekanntes Schriftformat gefunden: nicht als 0 Zeichen interpretieren."
        )
    for i, (start, font, pos, stride, legacy) in enumerate(entries):
        boundary = entries[i + 1][0] if i + 1 < len(entries) else len(data)
        glyphs = bytearray()
        limit = data[start + 285] if stride == 587 or legacy in ('eva2p12', 'grotesk1_number') else 10000
        while pos + 10 <= len(data) and pos < boundary and len(glyphs) < limit:
            if legacy == 'grotesk1_number':
                valid = _grotesk1_number_glyph(data, pos)
            elif legacy == 'eva2p12':
                valid = _eva2p12_glyph(data, pos)
            elif stride == 587:
                valid = _wide_587_record(data, pos)
            elif font == "EVA2NEU V1.1" and stride == 98:
                valid = (data[pos + 1] in (0x7D, 0x80, 0x81)
                         and data[pos + 7:pos + 10] == b"\x81\x00\x00")
            elif legacy:
                valid = ((data[pos + 1] in (0x80, 0x81, 0x82)
                          and data[pos + 7] in (0x80, 0x81))
                         or (data[pos + 1] in (0x7E, 0x7F)
                             and data[pos + 7] == 0x81))
            else:
                valid = (data[pos + 1] in ((0x7D, 0x7F, 0x80, 0x81, 0x82) if stride == 98 else (0x7E, 0x80, 0x81, 0x82))
                         and data[pos + 7:pos + 10] == b"\x81\x00\x00")
            if not valid:
                break
            glyphs.append(data[pos])
            pos += stride
        if glyphs:
            lines.append((font, bytes(glyphs)))
            if (stride == 587 or legacy in ('eva2p12', 'grotesk1_number')) and len(glyphs) != limit:
                warnings.append(f"{font}: historische Zeile unvollstaendig.")
            if len(glyphs) == 10000:
                warnings.append(f"{font}: Sicherheitslimit erreicht; moeglicherweise unvollstaendig.")
        else:
            warnings.append(f"{font} bei Offset {start}: unbekannte Struktur, nicht gezaehlt.")
    return lines, warnings
