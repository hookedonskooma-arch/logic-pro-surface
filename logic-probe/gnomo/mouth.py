"""GNOMO's mouth: a thin companion-level wrapper over the one mouth.

The lexicon, the secret filter, the Reed/Samantha preference and the spoken
log all live in `voz.mouth`. This adds only what is companion-specific: the
mute switch, and the result shape GNOMO's decision records expect.

There is no second TTS path here and there must never be one. A test asserts
that no file outside voz/ invokes `say`.
"""

from __future__ import annotations

import os
from typing import Any

from voz import mouth as _voz

MUTE_ENV = "GNOMO_MUTE"


def available() -> tuple[bool, str]:
    if os.environ.get(MUTE_ENV) == "1":
        return False, f"{MUTE_ENV}=1"
    return _voz.say_available()


def speak(text: str, *, timeout: float = 30.0) -> dict[str, Any]:
    """Say it out loud if we honestly can. Always report which happened."""
    text = text.strip()
    if not text:
        return {"spoke": False, "reason": "nothing to say", "text": text, "channel": None}

    ok, why = available()
    if not ok:
        return {"spoke": False, "reason": why, "text": text, "channel": None}

    result = _voz.speak(text, timeout=timeout)
    if not result.get("spoke"):
        return {
            "spoke": False,
            "reason": result.get("reason", "unknown"),
            "text": text,
            "channel": None,
        }
    return {
        "spoke": True,
        "reason": result.get("reason", "macOS say"),
        "text": text,
        "channel": "macos_say",
        "evidence": [
            f"voice: {result.get('voice')}",
            f"spoken: {result.get('spoken')}",
            f"logged: {result.get('logged')}",
        ],
    }
