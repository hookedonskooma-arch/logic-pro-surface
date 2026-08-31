"""Text and voice front ends. `python -m chatbot [--voice] [--speak]`."""

from __future__ import annotations

import argparse
import os
import sys
import tempfile

from . import voice as voice_mod
from .bot import HELP, MusicalChatBot

QUIT = {"quit", "exit", "bye", "stop"}


def _report(probes: list[voice_mod.Probe], kind: str) -> None:
    print(f"  {kind}:", file=sys.stderr)
    for probe in probes:
        mark = "READY  " if probe.available else "MISSING"
        print(f"    {mark} {probe.name}: {probe.detail}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="chatbot", description=__doc__)
    parser.add_argument("--voice", action="store_true",
                        help="listen on the default input instead of reading stdin")
    parser.add_argument("--speak", action="store_true", help="speak replies aloud")
    parser.add_argument("--seconds", type=float, default=6.0,
                        help="how long each --voice take records (default 6)")
    parser.add_argument("--probe", action="store_true",
                        help="report which local speech backends are installed, then exit")
    parser.add_argument("--key", help='start in a key, e.g. "F# dorian"')
    parser.add_argument("--tempo", type=float, help="start at this BPM")
    args = parser.parse_args(argv)

    recognizer, in_probes = voice_mod.first_available_recognizer()
    speaker, out_probes = voice_mod.first_available_speaker()

    if args.probe:
        print("Local speech backends:", file=sys.stderr)
        _report(in_probes, "speech to text")
        _report(out_probes, "text to speech")
        return 0

    bot = MusicalChatBot()
    if args.key:
        print(bot.respond(f"key of {args.key}").reply)
    if args.tempo:
        print(bot.respond(f"{args.tempo:g} bpm").reply)

    if args.voice and recognizer is None:
        print("No local recognizer available; falling back to typed input.", file=sys.stderr)
        _report(in_probes, "speech to text")
        args.voice = False
    if args.speak and speaker is None:
        print("No local speech synthesis available; replies stay on screen.", file=sys.stderr)
        _report(out_probes, "text to speech")
        args.speak = False

    print(HELP)
    while True:
        try:
            said = _listen(recognizer, args.seconds) if args.voice else input("you> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        except RuntimeError as error:  # capture or transcription failed
            print(f"[voice] {error}", file=sys.stderr)
            return 1
        if said is None:
            continue
        if said.strip().lower() in QUIT:
            return 0
        turn = bot.respond(said)
        if args.voice:
            print(f"you> {said}")
        print(turn.reply)
        if args.speak and turn.spoken:
            speaker.say(turn.spoken)


def _listen(recognizer: voice_mod.Recognizer, seconds: float) -> str | None:
    input("[press return, then speak] ")
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as handle:
        path = handle.name
    try:
        voice_mod.record_wav(path, seconds=seconds)
        said = recognizer.transcribe(path)
    finally:
        os.unlink(path)
    return said or None


if __name__ == "__main__":
    raise SystemExit(main())
