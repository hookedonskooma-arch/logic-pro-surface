"""Host detection. Fail closed. Never invent a live Logic session."""

from __future__ import annotations

import os
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
    return info


def logic_reachable() -> bool:
    return bool(detect()["logic_reachable"])
