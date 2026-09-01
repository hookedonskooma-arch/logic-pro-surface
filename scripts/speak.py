#!/usr/bin/env python3
"""v0 mouth: offline macOS `say`. MELEGI is MIDI FX, not TTS."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = REPO_ROOT / "studio" / "datasets" / "spoken.jsonl"

PREFERRED_VOICES = ("Reed (English (US))", "Samantha")

# Order matters: aumi / AUv3 before AU so we do not split them.
# Scripter, fader, bus, send, bounce are already English words.
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
        proc = subprocess.run(
            ["say", "-v", "?"],
            capture_output=True,
            text=True,
            check=False,
        )
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


def append_log(record: dict) -> bool:
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        return True
    except OSError:
        return False


def speak(text: str) -> int:
    spoken = apply_lexicon(text)
    voice = pick_voice()
    if voice is None:
        print("no v0 voice: need Reed (English (US)) or Samantha", file=sys.stderr)
        return 1
    try:
        proc = subprocess.run(["say", "-v", voice, spoken], check=False)
    except FileNotFoundError:
        print("say not found; v0 mouth is macOS-only", file=sys.stderr)
        return 1

    skip = should_skip_log(text) or should_skip_log(spoken)
    logged = False
    if skip:
        print(skip, file=sys.stderr)
    else:
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "role": os.environ.get("STUDIO_ROLE", "logic-studio"),
            "user": os.environ.get("STUDIO_USER", "chris"),
            "said": text,
            "spoken": spoken,
            "probe_status": None,
            "evidence": f"say -v {voice}; returncode={proc.returncode}",
        }
        logged = append_log(record)

    print(f"voice: {voice}")
    print(f"said: {text}")
    print(f"spoken: {spoken}")
    print(f"logged: {logged}")
    print(f"say_returncode: {proc.returncode}")
    return 0 if proc.returncode == 0 else proc.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "v0 TTS mouth via macOS say. MELEGI is MIDI FX, not the mouth. Offline."
        )
    )
    parser.add_argument(
        "text",
        help="text to speak (Logic vocabulary, never songs or secrets)",
    )
    args = parser.parse_args(argv)
    return speak(args.text)


if __name__ == "__main__":
    raise SystemExit(main())
