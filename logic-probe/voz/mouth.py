"""The single spoken-output implementation: lexicon, filter, voice, log.

Callers: scripts/speak.py (thin CLI), gnomo.mouth (companion), and any future
speaker. Nothing else may invoke `say` - tests enforce that.

What this owns, and what a second mouth would silently lose:

- **The lexicon.** studio/VOICE.md maps AU, AUv3, MCU, IAC, aumi to spelled
  forms. Fluency here is defined as Logic vocabulary in the spoken text.
- **The secret filter.** Never log a line carrying a key, token, or password.
- **The voice.** Reed, then Samantha. Never the arbitrary system default.
- **The log.** studio/datasets/spoken.jsonl, so what was said is auditable.

This module cannot hear. It speaks and it writes a record. Nothing else.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
LOG_PATH = REPO_ROOT / "studio" / "datasets" / "spoken.jsonl"

PREFERRED_VOICES = ("Reed (English (US))", "Samantha")

# Order matters: aumi / AUv3 before AU so we do not split them.
LEXICON: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\baumi\b", re.IGNORECASE), "A U M I"),
    (re.compile(r"\bauv3\b", re.IGNORECASE), "A U v 3"),
    (re.compile(r"\bau\b", re.IGNORECASE), "A U"),
    (re.compile(r"\bmcu\b", re.IGNORECASE), "M C U"),
    (re.compile(r"\biac\b", re.IGNORECASE), "I A C"),
]

_SECRET_MARKERS = (
    "api_key",
    "api-key",
    "secret",
    "token=",
    "bearer ",
    "sk-",
    "-----begin",
    "password",
)


def apply_lexicon(text: str) -> str:
    spoken = text
    for pattern, repl in LEXICON:
        spoken = pattern.sub(repl, spoken)
    return spoken


def list_voice_catalog() -> str:
    try:
        proc = subprocess.run(["say", "-v", "?"], capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return ""
    return proc.stdout or ""


def pick_voice() -> str | None:
    catalog = list_voice_catalog()
    for name in PREFERRED_VOICES:
        if name in catalog:
            return name
    return None


def should_skip_log(text: str) -> str | None:
    lower = text.lower()
    for marker in _SECRET_MARKERS:
        if marker in lower:
            return f"refusing to log: matched {marker!r}"
    return None


def append_log(record: dict[str, Any]) -> bool:
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        return True
    except OSError:
        return False


def say_available() -> tuple[bool, str]:
    if shutil.which("say") is None:
        return False, "macOS `say` not on this host; the v0 mouth is macOS-only"
    return True, "macOS say"


def speak(text: str, *, timeout: float = 120.0) -> dict[str, Any]:
    """Speak one line. Always report whether it was actually spoken.

    Printed text is not speech, the same way a sent MIDI byte is not a
    confirmed fader, so `spoke` is False whenever the mouth could not run.
    """
    text = text.strip()
    if not text:
        return {"spoke": False, "reason": "nothing to say", "text": text, "spoken": None}

    ok, why = say_available()
    if not ok:
        return {"spoke": False, "reason": why, "text": text, "spoken": None}

    spoken = apply_lexicon(text)
    voice = pick_voice()
    if voice is None:
        return {
            "spoke": False,
            "reason": "no v0 voice: need Reed (English (US)) or Samantha",
            "text": text,
            "spoken": spoken,
        }

    try:
        proc = subprocess.run(["say", "-v", voice, spoken], check=False, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"spoke": False, "reason": f"say failed: {exc}", "text": text, "spoken": spoken}

    skip = should_skip_log(text) or should_skip_log(spoken)
    logged = False
    if not skip:
        logged = append_log(
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "role": os.environ.get("STUDIO_ROLE", "logic-studio"),
                "user": os.environ.get("STUDIO_USER", "chris"),
                "said": text,
                "spoken": spoken,
                "probe_status": None,
                "evidence": f"say -v {voice}; returncode={proc.returncode}",
            }
        )

    return {
        "spoke": proc.returncode == 0,
        "reason": "macOS say" if proc.returncode == 0 else f"say returncode={proc.returncode}",
        "text": text,
        "spoken": spoken,
        "voice": voice,
        "logged": logged,
        "log_skipped": skip,
        "returncode": proc.returncode,
    }
