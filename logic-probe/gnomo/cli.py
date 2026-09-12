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

from . import ledger, mouth, persona, state, walkthrough
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


def _emit(
    payload: dict[str, Any],
    spoken: str,
    *,
    as_json: bool,
    quiet: bool,
    header: bool = True,
) -> int:
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

    if header:
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


def cmd_setup(args: argparse.Namespace) -> int:
    """One step at a time. The gnome does the IAC half; Logic's window needs hands."""
    fixed: dict[str, Any] = {}
    if args.fix:
        try:
            from logic_probe import midi_io

            fixed = midi_io.ensure_iac_mcu_buses()
        except Exception as exc:  # noqa: BLE001 — report, never claim it worked
            fixed = {"attempted": True, "error": f"{type(exc).__name__}: {exc}"}
    fix_failed = bool(args.fix and fixed.get("error"))

    results = walkthrough.evaluate()
    step = walkthrough.current(results)

    payload: dict[str, Any] = {
        "companion": "GNOMO",
        "command": "setup",
        "hat": args.hat,
        "tier": 0,
        "authority": "act",
        "mode": "for",
        "action": "check the MCU setup and name the one next step",
        "steps": results,
        "current_step": step["step"] if step else None,
    }
    if args.fix:
        payload["iac_fix"] = fixed

    if step is None:
        return _emit(
            payload,
            "MCU echo confirmed. Setup is done.",
            as_json=args.json,
            quiet=args.quiet,
        )

    spoken = step["spoken"]
    if fix_failed:
        spoken = "I could not make the buses myself. Do step one by hand."
    if not args.json:
        print(persona.hat_line(args.hat))
        if fix_failed:
            # A failed --fix is never a dead end: say what broke, then still
            # give the step. "Error, no next action" is the one outcome this
            # command must never produce.
            print(f"I could not make the buses: {fixed['error']}")
            print()
        done = sum(1 for r in results if r["state"] == walkthrough.DONE)
        print(f"step {done + 1} of {len(results)}: {step['title']}")
        print()
        for line in step["detail"]:
            print(f"  {line}")
        if fix_failed and step["manual"]:
            print()
            for line in step["manual"]:
                print(f"  {line}")
        if step["trap"]:
            print()
            print(f"  TRAP: {step['trap']}")
        if step["state"] == walkthrough.UNKNOWN:
            print()
            print(f"  I cannot verify this one from here ({step['evidence']}).")
            print("  Step 5's MCU echo is the only honest pass bit.")
        print()
        if not args.all:
            print("  Do that one. Then run this again.")
        else:
            print("  Remaining:")
            for row in results:
                mark = {"done": "x", "todo": " ", "unknown": "?"}[row["state"]]
                print(f"    [{mark}] {row['step']}: {row['title']}")
        print()

    return _emit(payload, spoken, as_json=args.json, quiet=args.quiet, header=False)


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

    setup = sub.add_parser("setup", help="guided setup, one step at a time")
    setup_sub = setup.add_subparsers(dest="target", required=True)
    mcu = setup_sub.add_parser("mcu", help="Mackie Control over IAC (E06)")
    mcu.add_argument(
        "--fix",
        action="store_true",
        help="let GNOMO create the two IAC buses (the half that needs no hands)",
    )
    mcu.add_argument("--all", action="store_true", help="also list the remaining steps")
    mcu.set_defaults(func=cmd_setup)

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
