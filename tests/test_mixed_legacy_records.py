"""Regression tests for preserved 1992 glyphs in edited SignumNext files."""
import unittest

from TB2_Textfinder import contains_term


def mixed_glyphs(text: str, stride: int, pair: bytes = b"\xcb\xcc") -> bytes:
    """Construct the observed first-glyph / continuation-glyph structure."""
    data = bytearray(stride * len(text) + 16)
    for i, char in enumerate(text):
        pos = 3 + i * stride
        data[pos] = ord(char)
        data[pos + 1] = 0x82
        data[pos + 7:pos + 10] = (
            b"\x81\x00\x00" if i == 0 else b"\x80" + pair
        )
    return bytes(data)


class MixedLegacyGlyphTests(unittest.TestCase):
    def test_1992_original_80_byte_records(self):
        self.assertTrue(contains_term(mixed_glyphs("Gerken", 80), "Gerken"))

    def test_2026_resaved_106_byte_records(self):
        self.assertTrue(contains_term(mixed_glyphs("Werner Gerken", 106), "Werner"))
        self.assertTrue(contains_term(mixed_glyphs("Lore Gerken", 106, b"\xb0\xdc"), "Lore"))

    def test_case_insensitive(self):
        self.assertTrue(contains_term(mixed_glyphs("Gerken", 106), "gerken"))
        self.assertFalse(contains_term(mixed_glyphs("Gerken", 106), "gerken", True))

    def test_reject_inconsistent_control_pair(self):
        data = bytearray(mixed_glyphs("Werner", 106))
        data[3 + 3 * 106 + 9] ^= 1
        self.assertFalse(contains_term(bytes(data), "Werner"))

    def test_reject_wrong_stride(self):
        self.assertFalse(contains_term(mixed_glyphs("Werner", 90), "Werner"))


if __name__ == "__main__":
    unittest.main()
