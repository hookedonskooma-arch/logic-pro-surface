"""Read Logic control-surface preference files. Observation only.

com.apple.logic.pro.cs is a little-endian FORM/SSCF blob, not a plist.
Do not edit it. Logic may rewrite it on quit.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

DEFAULT_CS = Path.home() / "Library/Preferences/com.apple.logic.pro.cs"
DEFAULT_PLIST = Path.home() / "Library/Preferences/com.apple.logic10.plist"

_CATALOG_MARKERS = (
    "Logic Control",
    "Mackie Control",
    "HUI",
    "iControl",
    "Logic Remote",
    "TouchOSC",
    "Launchpad",
)


def _printable_strings(data: bytes, min_len: int = 4) -> list[str]:
    out: list[str] = []
    cur = bytearray()
    for b in data:
        if 32 <= b < 127:
            cur.append(b)
        else:
            if len(cur) >= min_len:
                out.append(cur.decode("ascii"))
            cur = bytearray()
    if len(cur) >= min_len:
        out.append(cur.decode("ascii"))
    return out


def summarize(cs_path: Path | None = None) -> dict[str, Any]:
    path = cs_path or DEFAULT_CS
    info: dict[str, Any] = {
        "path": str(path),
        "exists": path.is_file(),
        "size": None,
        "magic": None,
        "catalog": [],
        "named_ports": [],
        "installed_hints": [],
        "iac_mentioned": False,
        "logic_control_in_catalog": False,
        "plist_exists": DEFAULT_PLIST.is_file(),
        "plist_path": str(DEFAULT_PLIST),
        "error": None,
    }
    if not path.is_file():
        info["error"] = "cs_prefs_missing"
        return info
    data = path.read_bytes()
    info["size"] = len(data)
    info["magic"] = data[:12].decode("latin1", "replace")
    strings = _printable_strings(data)
    catalog = []
    for marker in _CATALOG_MARKERS:
        if any(marker in s for s in strings):
            catalog.append(marker)
    info["catalog"] = catalog
    info["logic_control_in_catalog"] = "Logic Control" in catalog
    ports = []
    for s in strings:
        if s in ("SSL 2+", "Logic Pro Virtual In", "Logic Pro Virtual Out") or s.startswith(
            "IAC "
        ):
            if s not in ports:
                ports.append(s)
    info["named_ports"] = ports
    hints = []
    for s in strings:
        if "iPad" in s or s.startswith("Control Surface:") or "Remote (" in s:
            if s not in hints:
                hints.append(s)
    info["installed_hints"] = hints
    info["iac_mentioned"] = any("IAC" in s for s in strings)
    return info
