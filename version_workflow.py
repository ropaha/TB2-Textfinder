"""Versionen beider Programme prüfen und Releases ausdrücklich vorbereiten.

Beispiele:
    python version_workflow.py check --dev
    python version_workflow.py prepare-release
    python version_workflow.py check --release-tag v1.9.0

'prepare-release' ändert Dateien nur lokal; Commit, Merge, Tag und
Veröffentlichung erfolgen weiterhin nach ausdrücklicher Freigabe.
"""
import argparse
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
PROGRAMS = ("TB2_Textfinder.py", "TB2_Negativtester.py")
VERSION_RE = re.compile(r'^APP_VERSION\s*=\s*"(?P<version>\d+\.\d+\.\d+(?:-dev)?)"\s*$', re.MULTILINE)


def versions():
    result = {}
    for name in PROGRAMS:
        content = (ROOT / name).read_text(encoding="utf-8")
        matches = list(VERSION_RE.finditer(content))
        if len(matches) != 1:
            raise ValueError(f"{name}: genau eine gültige APP_VERSION erwartet")
        result[name] = matches[0].group("version")
    if len(set(result.values())) != 1:
        raise ValueError(f"Programmversionen stimmen nicht überein: {result}")
    return next(iter(result.values()))


def main():
    parser = argparse.ArgumentParser(description="Versionsworkflow für Finder und Negativtester")
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="Versionen und Branch-Konvention prüfen")
    group = check.add_mutually_exclusive_group(required=True)
    group.add_argument("--dev", action="store_true")
    group.add_argument("--release-tag", metavar="TAG")
    sub.add_parser("prepare-release", help="-dev entfernen und Changelog-Abschnitt abschließen")
    args = parser.parse_args()
    version = versions()
    if args.command == "check":
        if args.dev and not version.endswith("-dev"):
            parser.error(f"Dev-Build erwartet -dev, gefunden: {version}")
        if args.release_tag:
            if version.endswith("-dev"):
                parser.error("Ein Release darf kein -dev enthalten")
            if args.release_tag.lstrip("v") != version:
                parser.error(f"Release-Tag {args.release_tag} passt nicht zu {version}")
        print(f"Version geprüft: {version}")
        return

    if not version.endswith("-dev"):
        parser.error(f"Keine Entwicklungsversion: {version}")
    release = version.removesuffix("-dev")
    changelog_path = ROOT / "CHANGELOG.md"
    changelog = changelog_path.read_text(encoding="utf-8")
    heading = "## [Unveröffentlicht] – Entwicklungsbranch dev"
    if changelog.count(heading) != 1:
        parser.error("Erwarteter unveröffentlichter Changelog-Abschnitt fehlt oder ist doppelt")
    if f"## [{release}]" in changelog:
        parser.error(f"Changelog enthält bereits Version {release}")
    for name in PROGRAMS:
        path = ROOT / name
        content = path.read_text(encoding="utf-8")
        path.write_text(VERSION_RE.sub(
            lambda m: m.group(0).replace(version, release), content, count=1),
            encoding="utf-8")
    changelog_path.write_text(
        changelog.replace(heading, f"## [{release}] – Release", 1),
        encoding="utf-8")
    print(f"Release {release} lokal vorbereitet. Änderungen prüfen und erst nach Freigabe mergen.")


if __name__ == "__main__":
    main()
