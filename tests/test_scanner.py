import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from tb2.scanner import discover_files


class ScannerTests(unittest.TestCase):
    def test_recursive_and_flat(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "sub").mkdir()
            (root / "a.TB2").touch()
            (root / "sub" / "b.TbL").touch()
            (root / "ignore.txt").touch()
            (root / "directory.tb2").mkdir()
            for legacy in (False, True):
                for recursive in (False, True):
                    with self.subTest(legacy=legacy, recursive=recursive):
                        errors = []
                        paths, checked = discover_files(
                            root, recursive, threading.Event(), errors.append,
                            legacy_links=legacy)
                        expected = {root / "a.TB2"}
                        if recursive:
                            expected.add(root / "sub" / "b.TbL")
                        self.assertEqual(set(paths), expected)
                        self.assertEqual(checked, 3 if recursive else 1)
                        self.assertEqual(errors, [])

    def test_cancelled(self):
        with tempfile.TemporaryDirectory() as folder:
            stop = threading.Event()
            stop.set()
            for legacy in (False, True):
                self.assertEqual(discover_files(folder, True, stop, self.fail,
                                                legacy_links=legacy), ([], 0))

    def test_missing_root(self):
        with tempfile.TemporaryDirectory() as folder:
            for legacy in (False, True):
                errors = []
                paths, checked = discover_files(Path(folder) / "missing", False,
                                                threading.Event(), errors.append,
                                                legacy_links=legacy)
                self.assertEqual((paths, checked), ([], 0))
                self.assertEqual(len(errors), 1)

    def test_junction_pruned(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "junction").mkdir()
            (root / "junction" / "a.tb2").touch()
            with patch("os.path.isjunction", create=True,
                       side_effect=lambda path: Path(path).name == "junction"):
                for legacy in (False, True):
                    self.assertEqual(discover_files(root, True, threading.Event(),
                                                    self.fail, legacy_links=legacy), ([], 1))

    def test_progress(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for i in range(49):
                (root / str(i)).mkdir()
            progress = []
            paths, checked = discover_files(root, True, threading.Event(), self.fail,
                                            progress=lambda dirs, files: progress.append((dirs, files)))
            self.assertEqual((paths, checked), ([], 50))
            self.assertEqual(progress, [(50, 0)])
