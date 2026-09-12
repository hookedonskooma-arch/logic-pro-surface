#!/usr/bin/env python3
"""Thin CLI over the one mouth. The implementation lives in voz.mouth.

This file deliberately holds no lexicon, no filter and no voice list. It used
to, and that is how a second mouth got written: the logic was in a script,
so the next caller re-implemented it instead of importing it.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "logic-probe"))

from voz import mouth  # noqa: E402


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

    result = mouth.speak(args.text)

    if result.get("voice") is None:
        print(result["reason"], file=sys.stderr)
        return 1
    if result.get("log_skipped"):
        print(result["log_skipped"], file=sys.stderr)

    print(f"voice: {result['voice']}")
    print(f"said: {result['text']}")
    print(f"spoken: {result['spoken']}")
    print(f"logged: {result.get('logged', False)}")
    print(f"say_returncode: {result.get('returncode')}")
    return 0 if result.get("returncode") == 0 else int(result.get("returncode") or 1)


if __name__ == "__main__":
    raise SystemExit(main())
