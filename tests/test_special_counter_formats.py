import unittest

from tb2.muster import extract_counter_lines


class SpecialFormatTests(unittest.TestCase):
    def test_confirmed_profiles(self):
        cases = (
            (b"LUCIDA CALLIGRAPHY", 98, [(0x80, "810000")]),
            (b"CG TIMES (W1)", 98, [(0x81, "810000"), (0x81, "811142")]),
            (b"KAPTAL2", 98, [(0x80, "8096a8"), (0x81, "810000"),
                              (0x81, "80199c"), (0x7f, "805555"), (0x7f, "810000")]),
            (b"BRONZE\\STRASSACKER\\SCHWERE BLOCK", 106, [(0x80, "810000"), (0x81, "810000")]),
            (b"EVA4", 106, [(0x7d, "810000")]),
            (b"LAPIDAR1", 106, [(0x84, "810000")]),
        )
        for font, stride, markers in cases:
            with self.subTest(font=font):
                glyphs = b"AB\xfaCD"
                data = bytearray(344 + len(glyphs) * stride)
                data[0] = len(font)
                data[1:1 + len(font)] = font
                data[286] = len(glyphs)
                for i, char in enumerate(glyphs):
                    q = 344 + i * stride
                    marker, tail = markers[i % len(markers)]
                    data[q] = char
                    data[q + 1] = marker
                    data[q + 7:q + 10] = bytes.fromhex(tail)
                lines, warnings = extract_counter_lines(bytes(data))
                self.assertEqual(lines, [(font.decode().rsplit("\\", 1)[-1], glyphs)])
                self.assertEqual(warnings, [])
