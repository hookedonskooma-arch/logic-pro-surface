"""Grounding. GNOMO reads the studio markdown and nothing else.

Every fact the gnome speaks has to come from a file on disk that it names in
`grounded_in`. If a file is missing, the field is empty and the gnome says so.
It does not fill gaps with plausible studio-sounding text.

This module reads. It never reads Logic. Logic has no public project API.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
STUDIO = REPO_ROOT / "studio"

PROJECT_STATE = STUDIO / "PROJECT_STATE.md"
CURRENT_TASKS = STUDIO / "CURRENT_TASKS.md"
PARKING_LOT = STUDIO / "PARKING_LOT.md"

_BULLET = re.compile(r"^\s*[-*]\s+(.*\S)\s*$")
_HEADING = re.compile(r"^\s*#{1,6}\s+(.*\S)\s*$")


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def section(text: str, heading: str) -> list[str]:
    """Lines under a heading, up to the next heading of any level."""
    lines = text.splitlines()
    out: list[str] = []
    inside = False
    for line in lines:
        match = _HEADING.match(line)
        if match:
            if inside:
                break
            inside = match.group(1).strip().lower() == heading.strip().lower()
            continue
        if inside and line.strip():
            out.append(line.rstrip())
    return out


def _bullets(lines: list[str]) -> list[str]:
    found = []
    for line in lines:
        match = _BULLET.match(line)
        if match:
            found.append(match.group(1))
    return found


def blockers() -> tuple[list[str], list[str]]:
    """Known blockers plus the files they were read from."""
    text = _read(PROJECT_STATE)
    if text is None:
        return [], []
    return _bullets(section(text, "Known blockers")), [str(PROJECT_STATE.relative_to(REPO_ROOT))]


def now_task() -> tuple[str | None, list[str], list[str]]:
    """The single NOW item, its detail bullets, and the source file.

    CURRENT_TASKS.md writes NOW as a lead line plus bullets. The lead line is
    the one thing. Bullets are its detail, not extra tasks.
    """
    text = _read(CURRENT_TASKS)
    if text is None:
        return None, [], []
    lines = section(text, "NOW")
    source = [str(CURRENT_TASKS.relative_to(REPO_ROOT))]
    lead = next((ln.strip() for ln in lines if not _BULLET.match(ln)), None)
    return lead, _bullets(lines), source


def snapshot() -> dict[str, Any]:
    """Everything the gnome is allowed to know, with receipts."""
    blocking, blocker_src = blockers()
    lead, detail, task_src = now_task()
    grounded = blocker_src + task_src
    return {
        "now": lead,
        "now_detail": detail,
        "blockers": blocking,
        "grounded_in": grounded,
        "unknown": [] if grounded else ["studio/ markdown not readable from here"],
        "can_hear_audio": False,
        "can_read_logic_project": False,
    }
