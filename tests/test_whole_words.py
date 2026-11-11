"""Regressionstests für die experimentelle Ganzwortsuche."""
import unittest
from tb2_whole_words import contains_whole_word

def glyphs(text, stride=106):
    data = bytearray(stride * len(text) + 12)
    for i, ch in enumerate(text):
        pos = i * stride
        data[pos] = ord(ch)
        data[pos+1:pos+4] = b"\x81\x00\x00"
    return bytes(data)

class WholeWordTests(unittest.TestCase):
    def test_plain(self):
        for text, expected in [
            ("Hagen", True), ("Brigitte Wittenhagen", False),
            ("Hagenberg", False), ("Müller-Hagen", True),
            ("Hagen-Müller", True), ("(Hagen)", True),
            ("WITTENHAGEN", False), ("HAGEN", True)
        ]:
            with self.subTest(text=text):
                self.assertEqual(contains_whole_word(text.encode("utf-8"), "Hagen"), expected)

    def test_glyph(self):
        for text, expected in [
            ("Hagen", True), ("Wittenhagen", False),
            ("Hagenberg", False), ("Müller-Hagen", True),
            ("Hagen-Müller", True), ("(Hagen)", True),
        ]:
            with self.subTest(text=text):
                self.assertEqual(contains_whole_word(glyphs(text), "Hagen"), expected)

if __name__ == "__main__":
    unittest.main()
