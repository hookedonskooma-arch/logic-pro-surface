"""Routing for the desk companion's typed input.

The companion window (companion/main.swift) is a face, not a brain: it
never decides, never speaks, and never invents a path to the ladder.
Everything typed goes through this table to exactly one CLI verb —

    next   → `python -m gnomo --json next`
    park   → `python -m gnomo --json park "<idea>"`
    decide → `python -m gnomo --json decide "<action>"`

`reject` is not a CLI verb. It means the input was empty (or a `park:`
with nothing after the colon) and the window must show a refusal bubble
instead of invoking the ladder at all. Printed text is not speech and a
rejected input is not a decision.

`plan <path>` compiles a MusicPlan JSON file. It is a tier-0 body verb of
the composition engine: it never reaches the ladder and never ledgers a
decision (the plan command records its own compile); it never plays sound
— playing is `gnomo play` with Chris's --go, from the terminal.

companion/main.swift's `submit(_:)` mirrors this table by hand in Swift.
If the table changes here, change the Swift in the same commit.
"""

from __future__ import annotations

import shlex

REJECT = "reject"

# Body commands: the window moving its own body. Closed sets, fail closed —
# an unknown walk target or zoom arg is a reject, never a guess. These
# verbs never reach the ladder and never ledger; they are not decisions.
WALK_TARGETS = {"here", "left", "right", "center", "random"}
ZOOM_ARGS = {"in", "out", "normal", "toggle"}


def route(typed: str) -> tuple[str, str | None]:
    """Map one typed line to (verb, argument) for the CLI bridge.

    Never raises. Never guesses. An unmatched line is a `decide`, and an
    empty anything is a `reject` — fail closed, the same way the ladder
    does: absence of a rule is absence of permission, not permission by
    absence.

    Ladder verbs: next / park / decide (the studio, ledgered).
    Body verbs: walk / point / zoom (the window's own body, not ledgered
    — moving a gnome is not a decision about the studio).
    """
    raw = typed.strip()
    if not raw:
        return REJECT, None

    lower = raw.lower()

    if lower == "next":
        return "next", None

    if lower == "park" or lower.startswith("park:") or lower.startswith("park "):
        idea = None
        if lower.startswith("park:"):
            idea = raw[5:].strip() or None
        elif lower.startswith("park "):
            idea = raw[5:].strip() or None
        if idea is None:
            # `park` / `park:` / `park:   ` — nothing to catch.
            return REJECT, None
        return "park", idea

    if lower == "come" or lower == "come here" or lower == "comehere":
        return "walk", "here"
    if lower == "walk":
        return "walk", "random"
    if lower.startswith("walk "):
        target = lower[5:].strip()
        if target in WALK_TARGETS:
            return "walk", target
        return REJECT, None

    if lower == "point":
        return REJECT, None
    if lower.startswith("point "):
        return "point", raw[6:].strip()

    if lower == "zoom":
        return "zoom", "toggle"
    if lower.startswith("zoom "):
        arg = lower[5:].strip()
        if arg in ZOOM_ARGS:
            return "zoom", arg
        return REJECT, None

    if lower == "plan" or lower.startswith("plan ") or lower.startswith("plan:"):
        path = raw[5:].strip()
        if not path:
            return REJECT, None
        return "plan", path

    return "decide", raw


def cli_argv(verb: str, arg: str | None) -> list[str] | None:
    """Build the exact argv the window passes to `python -m gnomo`.

    Returns None for REJECT: a rejected input never reaches the ladder.

    This mirrors the bridge in companion/main.swift. It exists so tests
    can pin the exact command line — argument quoting included — without
    running the window.
    """
    if verb == REJECT:
        return None
    argv = ["-m", "gnomo", "--json", verb]
    if verb == "plan":
        # plan routes to the non-send compile: JSON out, quiet mouth.
        argv = ["-m", "gnomo", "--quiet", "--json", "plan", "--file", arg or ""]
        return argv
    if arg is not None:
        argv.append(arg)
    return argv


def quote_for_shell(argv: list[str]) -> str:
    """Human-readable shell form, for logs and docs. Not used to execute."""
    return " ".join(shlex.quote(part) for part in argv)