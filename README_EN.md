# TB2-Textfinder

A small Windows utility for searching text in `.TB2` files from different Signum / SignumNext file-format generations.

**Current development version:** 1.9.2-dev (latest release: 1.9.1)

![TB2-Textfinder project banner](images/banner.svg)

## Features

- Search a selected folder for `.TB2` files, optionally including subfolders.
- Search plain text and several empirically observed glyph/record patterns.
- Case-insensitive search by default, including German umlauts.
- Display full paths for matching files.
- Copy or save matching paths as a text file.
- Open a selected result with the Windows application associated with `.TB2` files, by double-clicking or using the **Datei öffnen** button.
- TB2 files are read-only; the tool does not modify them.

## Additional tools and settings

- Negative tester: review suspicious files, filter results and export TXT/diagnostic ZIP reports.
- Text counter: count characters (excluding spaces) and lines by font.
- Regression tester: create and compare JSON references, including glyph sequence hashes; start with `tools/Start_Regressiontester.bat`.
- Shared settings and the central SHA-256-based ignore list are stored in `%LOCALAPPDATA%\Signum Textfinder`. Existing `ignore.txt` files are imported once without modification. Changed files become eligible for review again.

## Interface preview

![Illustrative interface preview](images/screenshot.svg)

*Illustrative preview, not an actual screenshot of a running application. The real appearance may vary by version and Windows theme.*

## Run on Windows

Requirements: Windows and Python 3.10 or newer with Tkinter.

1. Download or clone this repository.
2. Double-click `Start_TB2_Textfinder.bat`.
3. Enter a search term, choose a folder, and click **Suchen** (Search).

No third-party packages are required to run the Python script directly. Keep the shared `tb2/` package in the project directory.

## Build a standalone Windows executable

1. Install Python 3.10 or newer.
2. Double-click `build/Build_EXE.bat`.
3. On the first run, an internet connection is needed to install PyInstaller.
4. The three executables are created in `dist`: `TB2_Textfinder.exe`, `TB2_Negativtester.exe` and `TB2_Textcounter.exe`.

The build script creates a local virtual environment in `.venv`, installs PyInstaller there, and builds a single-file, windowed executable. The Python runtime is bundled, so Python does not need to be installed on the target computer.

The manual GitHub Actions test build uploads all three executables in one artifact; official releases publish all three as individual assets. The regression tester remains an internal Python tool.

## Known format observations

The following patterns have been observed in the sample files examined so far:

- 106-byte record spacing (`0x6A`) with marker `81 00 00`.
- Another observed marker using the 106-byte spacing.
- Older 80-byte spacing (`0x50`) with marker `81 00 00`.
- Early 80-byte spacing (`0x50`) with marker `81 7C E9 E4 58 09`.
- Single-byte character encodings such as CP850, CP437, CP1252 and Latin-1 are considered for glyph profiles.

These observations are **not a complete or official specification** of the TB2 file format. They are empirical findings based on a limited set of sample files. A search miss does not prove that the text is absent from a file.

## Tests

The parser tests use synthetic byte sequences and do not require customer data:

```powershell
py -3 -m unittest discover -s tests -v
```

## Privacy

Searches run locally on your computer. The program does not upload TB2 files and does not modify them. Before sharing sample files, make sure they contain no customer or other confidential information.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).

## Disclaimer

This is an independent community project for investigating TB2 files. It is not affiliated with, endorsed by, or an official product of the Signum / SignumNext vendor.

## Central build system

`build/build.py` defines the shared PyInstaller configuration for local builds and both GitHub workflows. `build/Build_EXE.bat` is the single batch build launcher. Alternatively use `python build/build.py all --local`; individual targets are `textfinder`, `negativtester`, and `textcounter`. Use `--dry-run` to preview commands without building.
