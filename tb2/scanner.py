"""Shared TB2/TBL discovery, independent of GUI and file analysis."""
import os
from pathlib import Path


def discover_files(root, recursive, stop, on_error, *, legacy_links=False, progress=None):
    """Return paths and visited directory count, preserving caller link policy."""
    paths = []
    checked = 0

    def one_directory():
        try:
            with os.scandir(root) as entries:
                yield str(root), [], [entry.name for entry in entries
                                      if entry.is_file(follow_symlinks=False)]
        except OSError as exc:
            on_error(exc)

    directories = (one_directory() if legacy_links and not recursive else
                   os.walk(root, topdown=True, followlinks=False, onerror=on_error))
    for base, dirs, names in directories:
        if stop.is_set():
            break
        checked += 1
        dirs[:] = [d for d in dirs if recursive
                   and (legacy_links or not os.path.islink(os.path.join(base, d)))
                   and not getattr(os.path, "isjunction", lambda p: False)(os.path.join(base, d))]
        for name in names:
            if stop.is_set():
                break
            path = Path(base) / name
            matches = (name.lower().endswith((".tb2", ".tbl")) if legacy_links
                       else path.suffix.lower() in (".tb2", ".tbl"))
            if matches and (legacy_links or not path.is_symlink()):
                paths.append(path)
        if progress is not None and checked % 50 == 0:
            progress(checked, len(paths))
    return paths, checked
