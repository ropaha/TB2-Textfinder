"""Generate PyInstaller Windows VERSIONINFO resources."""
import re

DESCRIPTIONS = {
    "textfinder": "Signum TB2-Textfinder",
    "textcounter": "Signum TB2-Textcounter",
}


def version_resource(key, name, version, branch, commit, copyright_notice):
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:-[A-Za-z0-9.-]+)?", version)
    if not match:
        raise ValueError(f"Unsupported version: {version}")
    numbers = tuple(map(int, match.groups())) + (0,)
    if any(n > 65535 for n in numbers):
        raise ValueError("Windows version component exceeds 65535")
    fields = {
        "FileDescription": DESCRIPTIONS[key],
        "FileVersion": ".".join(map(str, numbers)),
        "ProductName": "Signum Textfinder",
        "ProductVersion": version,
        "LegalCopyright": copyright_notice,
        "OriginalFilename": name + ".exe",
        "InternalName": name,
        "Comments": f"Branch: {branch} | Commit: {commit} | MIT License",
    }
    strings = ",\n".join(f"StringStruct({k!r}, {v!r})" for k, v in fields.items())
    flags = 2 if "-" in version else 0
    return (
        "VSVersionInfo(\n"
        f"ffi=FixedFileInfo(filevers={numbers!r}, prodvers={numbers!r}, "
        f"mask=0x3f, flags={flags}, OS=0x40004, fileType=1, subtype=0, date=(0, 0)),\n"
        "kids=[StringFileInfo([StringTable('040704B0', [\n"
        + strings + "\n])]), VarFileInfo([VarStruct('Translation', [1031, 1200])])])\n"
    )
