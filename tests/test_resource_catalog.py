import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tb2.resource_catalog import scan_resources, save_catalog, load_catalog

class ResourceCatalogTests(unittest.TestCase):
    def test_recursive_inventory_and_roundtrip(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "sub").mkdir()
            (root / "sub" / "EVA4.fn3").write_bytes(b"abc")
            (root / "EVA4.FN3").write_bytes(b"x")
            (root / "test.ORN").write_bytes(b"")
            (root / "ignore.TB2").write_bytes(b"")
            progress = []
            data = scan_resources(root, progress=lambda done, total: progress.append((done, total)))
            self.assertEqual(data["schema"], 2)
            self.assertEqual(progress, [(0, 3), (1, 3), (2, 3), (3, 3)])
            self.assertEqual(len(data["resources"]["FN3"]), 2)
            self.assertEqual(data["resources"]["ORN"][0]["size"], 0)
            self.assertIn({"name": "EVA4.fn3", "path": "sub/EVA4.fn3", "size": 3, "sha256": hashlib.sha256(b"abc").hexdigest()}, data["resources"]["FN3"])
            self.assertEqual(sum(map(len, data["resources"].values())), 3)
            self.assertEqual(data["errors"], [])
            path = root / "settings" / "resources.json"
            with patch("tb2.resource_catalog.catalog_path", return_value=path):
                self.assertIsNone(load_catalog())
                save_catalog(data)
                self.assertEqual(load_catalog(), data)
                legacy = dict(data, schema=1)
                path.write_text(json.dumps(legacy), encoding="utf-8")
                self.assertEqual(load_catalog(), legacy)
                path.write_text("invalid", encoding="utf-8")
                self.assertIsNone(load_catalog())

if __name__ == "__main__":
    unittest.main()
