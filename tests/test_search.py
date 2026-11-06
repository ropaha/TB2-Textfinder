import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("tb2_textfinder", ROOT / "TB2_Textfinder.py")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class GlyphSearchTests(unittest.TestCase):
    def make_records(self, text: str, stride: int, marker: bytes, encoding: str = "cp850") -> bytes:
        data = bytearray(stride * max(len(text), 1) + len(marker) + 8)
        first = 8
        for index, char in enumerate(text):
            encoded = char.encode(encoding)
            if len(encoded) != 1:
                raise ValueError(f"{char!r} ist in {encoding} kein Ein-Byte-Zeichen")
            position = first + index * stride
            data[position] = encoded[0]
            data[position + 1:position + 1 + len(marker)] = marker
        return bytes(data)

    def test_106_byte_profile(self):
        data = self.make_records("Sindt", 0x6A, b"\x81\x00\x00")
        self.assertTrue(MODULE.contains_term(data, "Sindt"))

    def test_80_byte_older_profile(self):
        data = self.make_records("Araxi", 0x50, b"\x81\x00\x00")
        self.assertTrue(MODULE.contains_term(data, "Araxi"))

    def test_80_byte_early_profile(self):
        marker = b"\x81\x7C\xE9\xE4\x58\x09"
        data = self.make_records("Steen", 0x50, marker)
        self.assertTrue(MODULE.contains_term(data, "Steen"))

    def test_umlaut_case_insensitive(self):
        data = self.make_records("Müller", 0x6A, b"\x81\x00\x00", "cp850")
        self.assertTrue(MODULE.contains_term(data, "MÜLLER", case_sensitive=False))

    def test_case_sensitive_rejects_different_case(self):
        data = self.make_records("Sindt", 0x6A, b"\x81\x00\x00")
        self.assertFalse(MODULE.contains_term(data, "SINDT", case_sensitive=True))


if __name__ == "__main__":
    unittest.main()
