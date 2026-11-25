import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tb2 import settings


class ExportFolderTests(unittest.TestCase):
    def test_export_folders_are_independent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            config = root / "config" / "settings.json"
            other = root / "other"
            other.mkdir()
            with patch.object(settings, "settings_path", return_value=config):
                settings.remember_export_folder(root)
                settings.remember_json_folder(other)
                self.assertEqual(settings.load_export_folder(), str(root))
                self.assertEqual(settings.load_json_folder(), str(other))
                settings.remember_export_folder(other)
                settings.remember_json_folder(root)
                self.assertEqual(settings.load_export_folder(), str(other))
                self.assertEqual(settings.load_json_folder(), str(root))
                settings.remember_folder(root)
                self.assertEqual(settings.load_folder(), "")
                settings.remember_export_folder(root / "missing")
                self.assertEqual(settings.load_export_folder(), str(other))

    def test_empty_json_folder(self):
        with patch.object(settings, "load_settings", return_value={}):
            self.assertEqual(settings.load_json_folder(), "")

    def test_write_failure_logged(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(settings, "settings_path", return_value=Path(tmp) / "settings.json"):
                with patch.object(settings.os, "replace", side_effect=OSError("test")):
                    with self.assertLogs("tb2.settings", level="ERROR"):
                        settings.save_option("export_folder", tmp)


if __name__ == "__main__":
    unittest.main()
