"""CLI: python -m gnomo <command> ...

Every command answers the same question in the same shape: who decided this,
GNOMO or you? Exit code 0 means a decision was printed. Read `tier` for the
semantics, the same way logic_probe makes you read `status`.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import ledger, mouth, persona, state
from .ladder import TIER_ACT, TIER_REFUSE, decide

EXIT_OK = 0


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _park(idea: str) -> tuple[bool, str]:
    """Catch the idea so it stops competing with the one thing."""
    path = state.PARKING_LOT
    stamp = _utc_now_iso()
    try:
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "# Parking lot\n\n"
                "Ideas GNOMO caught so the hands could finish the one thing.\n"
                "Nothing here is a commitment, a task, or a claim about Logic.\n\n",
                encoding="utf-8",
            )
        with path.open("a", encoding="utf-8") as fh:
            fh.write(f"- [{stamp}] {idea.strip()}\n")
    except OSError as exc:
        return False, f"parking lot write failed: {exc}"
    try:
        return True, str(path.relative_to(state.REPO_ROOT))
    except ValueError:
        # A lot outside the repo is still a lot. Never lose the idea over a path.
        return True, str(path)


def _emit(payload: dict[str, Any], spoken: str, *, as_json: bool, quiet: bool) -> int:
    # Hand-built payloads (say, park) do not come from ladder.decide(), so they
    # arrive unstamped. An undated ledger row is not an audit trail.
    payload.setdefault("timestamp", _utc_now_iso())
    said = None if quiet else mouth.speak(spoken)
    payload["spoken"] = spoken
    payload["voice"] = said or {"spoke": False, "reason": "--quiet"}

    logged, where = ledger.append(payload)
    payload["ledger"] = {"written": logged, "path": where}

    if as_json:
        json.dump(payload, sys.stdout, indent=2, sort_keys=False)
        sys.stdout.write("\n")
        return EXIT_OK

    print(persona.hat_line(payload.get("hat", "engineer")))
    print(spoken)
    if not payload["voice"].get("spoke"):
        print(f"(not spoken: {payload['voice'].get('reason')})")
    return EXIT_OK


def cmd_next(args: argparse.Namespace) -> int:
    snap = state.snapshot()
    action = snap.get("now") or "decide the one thing"
    decision = decide(
        action,
        hat=args.hat,
        blockers=tuple(snap.get("blockers") or ()),
        grounded_in=tuple(snap.get("grounded_in") or ()),
    )
    decision["command"] = "next"
    decision["state"] = snap
    return _emit(decision, persona.brief(snap, decision), as_json=args.json, quiet=args.quiet)


def cmd_decide(args: argparse.Namespace) -> int:
    snap = state.snapshot()
    decision = decide(
        args.action,
        hat=args.hat,
        blockers=tuple(snap.get("blockers") or ()),
        grounded_in=tuple(snap.get("grounded_in") or ()),
    )
    decision["command"] = "decide"
    return _emit(decision, persona.line(decision), as_json=args.json, quiet=args.quiet)


def cmd_say(args: argparse.Namespace) -> int:
    payload = {
        "companion": "GNOMO",
        "command": "say",
        "hat": args.hat,
        "tier": TIER_ACT,
        "authority": "act",
        "mode": "for",
        "action": f"say: {args.text}",
    }
    return _emit(payload, persona.plain(args.text), as_json=args.json, quiet=args.quiet)


def cmd_park(args: argparse.Namespace) -> int:
    ok, where = _park(args.idea)
    payload = {
        "companion": "GNOMO",
        "command": "park",
        "hat": args.hat,
        "tier": TIER_ACT,
        "authority": "act",
        "mode": "for",
        "action": f"park: {args.idea}",
        "parked": ok,
        "parking_lot": where,
    }
    spoken = "Parked. Back to the one thing." if ok else f"Could not park it: {where}"
    return _emit(payload, spoken, as_json=args.json, quiet=args.quiet)


def cmd_ledger(args: argparse.Namespace) -> int:
    rows = ledger.read(args.limit)
    if args.json:
        json.dump(rows, sys.stdout, indent=2, sort_keys=False)
        sys.stdout.write("\n")
        return EXIT_OK
    if not rows:
        print("no decisions on record")
        return EXIT_OK
    for row in rows:
        mode = row.get("mode", "?")
        print(f"{row.get('timestamp', '?')}  [{mode:>5}]  {row.get('action', '')}")
    return EXIT_OK


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="gnomo",
        description=(
            "GNOMO, the studio gnome. One voice, one action, one ladder. "
            "Tier 0 acts for you, 1 acts with you, 2 is yours, 3 is never."
        ),
    )
    p.add_argument("--hat", default="engineer", help="which studio hat the gnome is wearing")
    p.add_argument("--json", action="store_true", help="print the full decision record")
    p.add_argument("--quiet", action="store_true", help="do not open the mouth")

    sub = p.add_subparsers(dest="command", required=True)

    nxt = sub.add_parser("next", help="the one thing to do now, from studio notes only")
    nxt.set_defaults(func=cmd_next)

    dec = sub.add_parser("decide", help="put one action on the ladder")
    dec.add_argument("action")
    dec.set_defaults(func=cmd_decide)

    say = sub.add_parser("say", help="speak a line in the gnome's voice")
    say.add_argument("text")
    say.set_defaults(func=cmd_say)

    park = sub.add_parser("park", help="catch an idea without derailing the one thing")
    park.add_argument("idea")
    park.set_defaults(func=cmd_park)

    led = sub.add_parser("ledger", help="recent decisions")
    led.add_argument("--limit", type=int, default=10)
    led.set_defaults(func=cmd_ledger)

    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        return args.func(args)
    except ValueError as exc:
        # An empty or unusable ask is not a decision. Say so, do not traceback.
        print(f"GNOMO: {exc}", file=sys.stderr)
        return 2
