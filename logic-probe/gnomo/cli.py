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

from . import hands, ledger, mouth, persona, state, walkthrough
from .ladder import TIER_ACT, TIER_REFUSE, decide
from .music_plan import MusicPlanError, load_plan, plan_from_json
from .midi_compiler import compile_plan, write_smf
from .seam import SeamError, play_plan

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


def _hands_line(record: dict[str, Any]) -> str:
    """What the gnome says about a hands request, in one breath."""
    verb, result = record["hands"]["verb"], record.get("result") or {}
    if record["tier"] == TIER_REFUSE:
        return f"No. {record['reason']}."
    status, reason = result.get("status"), result.get("reason")
    if reason == "not_macos":
        return "My hands only work on the Mac. Nothing was touched."
    if reason == "helper_not_built":
        return f"My hands aren't built yet. Run {hands.BUILD_HINT} on the Mac."
    if reason == "needs_accessibility_permission":
        return "macOS hasn't let me use my hands. Allow gnomo-hands under Privacy, Accessibility."
    if reason == "declined_by_human":
        return "You said not now. Nothing was touched."
    if reason == "human_took_over":
        return "You were moving, so I let go. Nothing was touched."
    if reason == "ambiguous":
        return "More than one thing matches. Pick one with --index."
    if reason == "not_found":
        return f"I can't see that in {result.get('app', 'the front app')}."
    if verb in ("look", "find") and result.get("ok"):
        return f"I see {len(result.get('elements') or [])} things in {result.get('app')}."
    if status == "attempted":
        label = (result.get("target") or {}).get("label")
        what = f" {label}" if label else ""
        return f"Done{what}, via {result.get('channel')}. That's a receipt, not proof it took."
    return f"Hands {verb} did not run ({reason or status})."


def cmd_hands(args: argparse.Namespace) -> int:
    target = " ".join(args.target).strip()
    try:
        record = hands.run(args.verb, target, index=args.index)
    except ValueError as exc:
        print(f"hands: {exc}", file=sys.stderr)
        return 2
    record["command"] = "hands"
    return _emit(record, _hands_line(record), as_json=args.json, quiet=args.quiet)


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


def cmd_plan(args: argparse.Namespace) -> int:
    """Tier 0: validate + compile a MusicPlan. No Logic, no ports, no send."""
    try:
        plan = load_plan(args.file) if args.file else plan_from_json(args.json_text)
        compiled = compile_plan(plan)
    except MusicPlanError as exc:
        payload = {
            "companion": "GNOMO",
            "command": "plan",
            "hat": args.hat,
            "tier": 0,
            "authority": "act",
            "mode": "for",
            "action": "validate + compile a music plan",
            "accepted": False,
            "error": str(exc),
        }
        return _emit(payload, f"Plan rejected: {exc}", as_json=args.json, quiet=args.quiet)

    out_path = None
    if args.out:
        out_path = write_smf(compiled, args.out)
    payload = {
        "companion": "GNOMO",
        "command": "plan",
        "hat": args.hat,
        "tier": 0,
        "authority": "act",
        "mode": "for",
        "action": "validate + compile a music plan",
        "accepted": True,
        "tempo": plan["tempo"],
        "meter": plan["meter"],
        "length_bars": plan["length_bars"],
        "chords": plan["chords"],
        "voicing": plan["voicing"],
        "register": plan["register"],
        "velocity_range": plan["velocity_range"],
        "event_count": compiled["event_count"],
        "phrase_hash": compiled["phrase_hash"],
        "smf_bytes": len(compiled["smf"]),
        "smf_path": out_path,
    }
    spoken = (
        f"Plan compiles. {plan['length_bars']} bars at {plan['tempo']}, "
        f"{compiled['event_count']} events, hash {compiled['phrase_hash']}."
    )
    return _emit(payload, spoken, as_json=args.json, quiet=args.quiet)


def cmd_play(args: argparse.Namespace) -> int:
    """Tier 1: play the compiled plan out CoreMIDI. Refuses without --go.

    The gnome compiles for free; making sound in the room is with you.
    Offline / missing ports land `uncertain` — the envelope says what is
    missing, never a fake send.
    """
    if not args.go:
        decision = decide(
            "play the compiled plan out CoreMIDI",
            hat=args.hat,
            blockers=("no --go on the play command",),
            grounded_in=("studio/FAILURE_DRIVEN_ARCHITECTURE.md",),
        )
        decision["command"] = "play"
        return _emit(
            decision,
            "Say the word: rerun with --go and I will make sound.",
            as_json=args.json,
            quiet=args.quiet,
        )

    try:
        plan = load_plan(args.file) if args.file else plan_from_json(args.json_text)
        compiled = compile_plan(plan)
    except MusicPlanError as exc:
        payload = {
            "companion": "GNOMO",
            "command": "play",
            "hat": args.hat,
            "tier": 0,
            "authority": "act",
            "mode": "for",
            "action": "compile the plan before playing",
            "accepted": False,
            "error": str(exc),
        }
        return _emit(payload, f"Plan rejected: {exc}", as_json=args.json, quiet=args.quiet)

    envelope = play_plan(
        compiled,
        out_port=args.out,
        capture_port=args.capture,
        force_offline=args.offline,
    )
    spoken_by_status = {
        "confirmed": (
            f"Capture matches the compile. Hash {compiled['phrase_hash']} — "
            "now your ears: does the instrument agree?"
        ),
        "failed": "Capture contradicts the compile. Something in the routing lies.",
        "uncertain": f"Uncertain: {envelope['adapter_result'].get('reason')}. Nothing claimed.",
    }
    payload = {
        "companion": "GNOMO",
        "command": "play",
        "hat": args.hat,
        "tier": 1,
        "authority": "propose",
        "mode": "with",
        "action": "play the compiled plan out CoreMIDI",
        "phrase_hash": compiled["phrase_hash"],
        "rollback": "stop the instrument track; nothing was written into the project",
        "envelope": envelope,
    }
    return _emit(
        payload,
        spoken_by_status.get(envelope["status"], "Seam returned an unknown status."),
        as_json=args.json,
        quiet=args.quiet,
    )


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
    if args.fix:
        try:
            from logic_probe import midi_io

            fixed = midi_io.ensure_iac_mcu_buses()
        except Exception as exc:  # noqa: BLE001 — report, never claim it worked
            fixed = {"attempted": True, "error": f"{type(exc).__name__}: {exc}"}
        if fixed.get("error"):
            payload = {
                "companion": "GNOMO",
                "command": "setup",
                "hat": args.hat,
                "tier": 2,
                "authority": "ask",
                "mode": "you",
                "action": "create the IAC MCU buses",
                "iac_fix": fixed,
            }
            return _emit(
                payload,
                f"Could not make the buses: {fixed['error']}.",
                as_json=args.json,
                quiet=args.quiet,
            )

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
    if not args.json:
        print(persona.hat_line(args.hat))
        done = sum(1 for r in results if r["state"] == walkthrough.DONE)
        print(f"step {done + 1} of {len(results)}: {step['title']}")
        print()
        for line in step["detail"]:
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

    hnd = sub.add_parser(
        "hands",
        help="look at / point at things in the front app; click, type, key only after a human 'Do it'",
    )
    hnd.add_argument("verb", choices=hands.VERBS)
    hnd.add_argument("target", nargs="*", help="label to find/point/click, text to type, or a key combo")
    hnd.add_argument("--index", type=int, help="which match, when a label matches more than one thing")
    hnd.set_defaults(func=cmd_hands)

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

    plan_p = sub.add_parser(
        "plan", help="validate + compile a MusicPlan (tier 0, no send)"
    )
    src = plan_p.add_mutually_exclusive_group(required=True)
    src.add_argument("--file", help="path to a MusicPlan JSON file")
    src.add_argument("--json-text", help="a MusicPlan as a JSON string")
    plan_p.add_argument("--out", help="write the SMF to this path (drag-in ready)")
    plan_p.set_defaults(func=cmd_plan)

    play = sub.add_parser(
        "play", help="play the compiled plan out CoreMIDI (tier 1, needs --go)"
    )
    psrc = play.add_mutually_exclusive_group(required=True)
    psrc.add_argument("--file", help="path to a MusicPlan JSON file")
    psrc.add_argument("--json-text", help="a MusicPlan as a JSON string")
    play.add_argument("--out", required=True, help="CoreMIDI output port name")
    play.add_argument(
        "--capture",
        help="independent CoreMIDI input port for the E12 capture (not the send port)",
    )
    play.add_argument(
        "--go", action="store_true", help="give the nod: actually send the notes"
    )
    play.add_argument(
        "--offline",
        action="store_true",
        help="force the offline contract (nothing opens, nothing sends)",
    )
    play.set_defaults(func=cmd_play)

    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        return args.func(args)
    except ValueError as exc:
        # An empty or unusable ask is not a decision. Say so, do not traceback.
        print(f"GNOMO: {exc}", file=sys.stderr)
        return 2
