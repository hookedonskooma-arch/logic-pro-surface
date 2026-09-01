"""Host detection. Fail closed. Never invent a live Logic session."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any


LOGIC_PROCESS_NAMES = ("Logic Pro", "Logic Pro X")


def _darwin_logic_running() -> bool:
    pgrep = shutil.which("pgrep")
    if pgrep is None:
        return False
    try:
        proc = subprocess.run(
            [pgrep, "-lf", "Logic Pro"],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    if proc.returncode not in (0, 1):
        return False
    for line in (proc.stdout or "").splitlines():
        # Require a real app name; do not match this repo's docs.
        if "Logic Pro.app" in line or "/Applications/Logic Pro" in line:
            return True
    return False



def _macos_version() -> str | None:
    try:
        import platform

        ver = platform.mac_ver()[0]
        return ver or None
    except Exception:
        return None


def _logic_version() -> str | None:
    info = Path("/Applications/Logic Pro.app/Contents/Info.plist")
    if not info.is_file():
        return None
    try:
        import plistlib

        data = plistlib.loads(info.read_bytes())
    except Exception:
        return None
    v = data.get("CFBundleShortVersionString")
    return str(v) if v else None


def detect() -> dict[str, Any]:
    """Return host facts. logic_reachable is True only with evidence."""
    platform = sys.platform
    info: dict[str, Any] = {
        "platform": platform,
        "logic_reachable": False,
        "logic_version": None,
        "macos_version": None,
        "reason": "logic_not_reachable",
        "channels_implemented": [],
    }
    if platform != "darwin":
        info["reason"] = "not_macos"
        return info
    if os.environ.get("LOGIC_PROBE_FORCE_OFFLINE") == "1":
        info["reason"] = "forced_offline"
        return info
    if not _darwin_logic_running():
        info["reason"] = "logic_process_not_found"
        return info
    # Process present is not a control channel. v0 still cannot confirm writes.
    info["logic_reachable"] = True
    info["reason"] = "logic_process_seen_no_channel"
    info["macos_version"] = _macos_version()
    info["logic_version"] = _logic_version()
    return info


def logic_reachable() -> bool:
    return bool(detect()["logic_reachable"])
