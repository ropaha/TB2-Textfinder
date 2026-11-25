"""Central Windows executable build for the three public TB2 tools."""
import argparse
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
TARGETS = {
    "textfinder": ("TB2_Textfinder", ()),
    "negativtester": ("TB2_Negativtester", ("TB2_Textfinder",)),
    "textcounter": ("TB2_Textcounter", ()),
}
RESOURCES = ("logo.ico", "CHANGELOG.md")


def command(key, output, work):
    name, hidden = TARGETS[key]
    for filename in (*RESOURCES, name + ".py"):
        if not (ROOT / filename).is_file():
            raise FileNotFoundError(ROOT / filename)
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
           "--onefile", "--windowed", "--icon", str(ROOT / "logo.ico")]
    for filename in RESOURCES:
        cmd.extend(["--add-data", str(ROOT / filename) + ";."])
    for module in hidden:
        cmd.extend(["--hidden-import", module])
    return cmd + ["--name", name, "--distpath", str(output),
                  "--workpath", str(work), "--specpath", str(work),
                  str(ROOT / (name + ".py"))]


def run(cmd):
    subprocess.run(cmd, cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("targets", nargs="*", metavar="TARGET",
                        help="all, textfinder, negativtester, textcounter")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--local", action="store_true",
                        help="Use the project's virtual environment and install build requirements")
    args = parser.parse_args()
    keys = args.targets or ["all"]
    if any(key not in (*TARGETS, "all") for key in keys):
        parser.error("Unknown build target")
    keys = list(TARGETS) if "all" in keys else list(dict.fromkeys(keys))
    if args.dry_run:
        for key in keys:
            print(subprocess.list2cmdline(command(key, ROOT / "dist", ROOT / "build" / key)))
        return
    if os.name != "nt":
        parser.error("Windows is required to build Windows EXEs")
    if sys.version_info < (3, 10):
        parser.error("Python 3.10 or newer is required")
    if args.local:
        env = ROOT / ".venv"
        python = env / "Scripts" / "python.exe"
        if not python.is_file():
            run([sys.executable, "-m", "venv", str(env)])
        run([str(python), "-m", "pip", "install", "-r", "requirements-build.txt"])
        run([str(python), str(Path(__file__).resolve()), *keys])
        return
    if importlib.util.find_spec("PyInstaller") is None:
        parser.error("Install requirements-build.txt first")
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    # A fresh staging directory prevents stale executables passing verification.
    # Only this newly created temporary directory is cleaned up.
    with tempfile.TemporaryDirectory(prefix=".tb2-build-", dir=dist) as temp:
        stage = Path(temp)
        for key in keys:
            name, _ = TARGETS[key]
            output = stage / "output"
            work = stage / key
            work.mkdir()
            cmd = command(key, output, work)
            print(subprocess.list2cmdline(cmd), flush=True)
            run(cmd)
            exe = output / (name + ".exe")
            if not exe.is_file() or exe.stat().st_size == 0:
                raise RuntimeError(f"Missing or empty executable: {exe}")
        for key in keys:
            name, _ = TARGETS[key]
            exe = stage / "output" / (name + ".exe")
            destination = dist / exe.name
            os.replace(exe, destination)
            print(f"OK: {destination}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Build failed: {exc}", file=sys.stderr)
        sys.exit(1)
