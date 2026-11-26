"""GUI-independent Signum character counting core."""
from tb2.muster import extract_counter_lines

SPACE_CODE = 0xFA

def counter_lines(data, mode):
    if mode != "fast":
        return extract_counter_lines(data)
    from tb2.jpeg_fast import jpeg_ranges
    spans = jpeg_ranges(data)
    if not spans:
        return extract_counter_lines(data)
    lines, warnings = [], []
    previous = 0
    for begin, end in spans + [(len(data), len(data))]:
        if begin > previous:
            part_lines, part_warnings = extract_counter_lines(data[previous:begin])
            lines.extend(part_lines)
            warnings.extend(w for w in part_warnings if not w.startswith("Kein bekanntes Schriftformat gefunden:"))
        previous = max(previous, end)
    if not lines:
        warnings.append("Kein bekanntes Schriftformat gefunden: nicht als 0 Zeichen interpretieren.")
    return lines, warnings
