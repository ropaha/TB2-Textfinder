import unittest
from tb2.metadata import extract_metadata, summarize_metadata

def field(value):
    return len(value).to_bytes(4, "little") + value

class MetadataTests(unittest.TestCase):
    def test_modern(self):
        data = bytes.fromhex("1411cdab") + field(b"11.27.1") + field(b"SignumNext.EXE")
        self.assertEqual(extract_metadata(data), dict(file_version="ABCD1114", format=None,
                         created_exe_version="11.27.1", created_exe_name="SignumNext.EXE"))
    def test_old(self):
        self.assertEqual(extract_metadata(bytes.fromhex("2507cdab"))["file_version"], "ABCD0725")
    def test_invalid(self):
        for data in (b"", b"abc", bytes.fromhex("048940fa")):
            self.assertIsNone(extract_metadata(data)["file_version"])
        self.assertIsNone(extract_metadata(bytes.fromhex("1411cdabffffffff"))["created_exe_version"])
    def test_summary(self):
        rows = [{"metadata": {"file_version": "ABCD0725"}, "status": "Prüfen"}, {"status": "Gezählt"}]
        result = summarize_metadata(rows)
        self.assertEqual(result["ABCD0725"]["statuses"]["Prüfen"], 1)
        self.assertEqual(result["Unbekannt"]["files"], 1)
