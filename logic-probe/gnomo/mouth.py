"""The mouth. One mouth, reused, never re-implemented.

Speech goes through scripts/speak.py (macOS `say`, Reed then Samantha, the
Logic lexicon, the secret filter, the spoken.jsonl log). This module adds no
second TTS path and no second lexicon.

Off macOS the gnome does not pretend. `spoke` is False and the reason says
why. Printed text is not speech, the same way a sent MIDI byte is not a
confirmed fader.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SPEAK_SCRIPT = REPO_ROOT / "scripts" / "speak.py"

MUTE_ENV = "GNOMO_MUTE"


def available() -> tuple[bool, str]:
    if os.environ.get(MUTE_ENV) == "1":
        return False, f"{MUTE_ENV}=1"
    if not SPEAK_SCRIPT.is_file():
        return False, "scripts/speak.py is missing"
    if shutil.which("say") is None:
        return False, "macOS `say` not on this host; the v0 mouth is macOS-only"
    return True, "macOS say via scripts/speak.py"


def speak(text: str, *, timeout: float = 30.0) -> dict[str, Any]:
    """Say it out loud if we honestly can. Always report which happened."""
    text = text.strip()
    if not text:
        return {"spoke": False, "reason": "nothing to say", "text": text, "channel": None}

    ok, why = available()
    if not ok:
        return {"spoke": False, "reason": why, "text": text, "channel": None}

    try:
        proc = subprocess.run(
            [sys.executable, str(SPEAK_SCRIPT), text],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"spoke": False, "reason": f"speak.py failed: {exc}", "text": text, "channel": None}

    if proc.returncode != 0:
        reason = (proc.stderr or "").strip() or f"speak.py returncode={proc.returncode}"
        return {"spoke": False, "reason": reason, "text": text, "channel": None}

    return {
        "spoke": True,
        "reason": why,
        "text": text,
        "channel": "macos_say",
        "evidence": (proc.stdout or "").strip().splitlines(),
    }
