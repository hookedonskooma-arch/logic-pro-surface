"""CLI: python -m logic_probe <command> ..."""

from __future__ import annotations

import argparse
import json
import sys

from . import channels


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="logic_probe",
        description="Fail-closed Logic Pro probes. Envelope status is confirmed|uncertain|failed.",
    )
    sub = p.add_subparsers(dest="group", required=True)

    mixer = sub.add_parser("mixer", help="mixer probes")
    mixer_sub = mixer.add_subparsers(dest="action", required=True)
    vol = mixer_sub.add_parser("set-volume", help="set track volume via MCU fader; confirmed only on echo")
    vol.add_argument("--track", type=int, required=True)
    vol.add_argument("--db", type=float, required=True)

    transport = sub.add_parser("transport", help="transport probes")
    transport_sub = transport.add_subparsers(dest="action", required=True)
    transport_sub.add_parser("play", help="play (v0: uncertain without MCU echo)")

    ax = sub.add_parser("ax", help="Accessibility probes (workaround; not a Logic API)")
    ax_sub = ax.add_subparsers(dest="action", required=True)
    ax_sub.add_parser("inspect-selected-track", help="inspect selected track (never fake confirmed)")

    return p


def dispatch(args: argparse.Namespace) -> dict:
    if args.group == "mixer" and args.action == "set-volume":
        return channels.mixer_set_volume(args.track, args.db)
    if args.group == "transport" and args.action == "play":
        return channels.transport_play()
    if args.group == "ax" and args.action == "inspect-selected-track":
        return channels.ax_inspect_selected_track()
    raise SystemExit(f"unhandled command: {args.group} {getattr(args, 'action', '')}")


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    envelope = dispatch(args)
    json.dump(envelope, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")
    # Exit 0 = envelope printed. Read envelope["status"] for semantics.
    return 0
