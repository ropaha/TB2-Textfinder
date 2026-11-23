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



