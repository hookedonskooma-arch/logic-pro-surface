"""GNOMO's hands: look at, point at, and (with a human yes) press things in other apps.

Two halves, two jobs:

- This module is the *authority* half. Every request goes on the decision
  ladder before anything runs. Tier 3 is refused here and never reaches the
  helper. Looking and pointing change nothing, so they are tier 0 unless the
  ladder refuses them.
- `companion/gnomo-hands` (Swift, macOS) is the *hands* half. It shows a native
  "Do it" dialog before every click, keystroke or key combo. There is no flag,
  mode or environment variable that skips that dialog, so a script driving
  this CLI cannot approve its own clicks.

Honest contract: the helper reports `attempted` and names the channel
(ax_press, cgevent_click, cgevent_keys, cgevent_move). That is a receipt, not
a confirmed state change. Nothing here ever prints `confirmed`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from .ladder import TIER_ACT, TIER_REFUSE, decide

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_HELPER = REPO_ROOT / "companion" / "build" / "gnomo-hands"
BUILD_HINT = "companion/build_hands.sh"

OBSERVE_VERBS = ("look", "find", "point")   # change nothing in the target app
ACT_VERBS = ("click", "type", "key")        # each one waits for the human's "Do it"
VERBS = OBSERVE_VERBS + ACT_VERBS

# The helper waits on a person for act verbs; give them time to read the dialog.
TIMEOUT_OBSERVE_S = 20
TIMEOUT_ACT_S = 180


def helper_path() -> Path:
    return Path(os.environ.get("GNOMO_HANDS_BIN") or DEFAULT_HELPER)


def describe(verb: str, target: str) -> str:
    """The sentence the ladder judges. Says what the hands would do, in words."""
    if verb == "look":
        return "look at the front window" + (f" in {target}" if target else "")
    if verb == "find":
        return f"find {target} on screen"
    if verb == "point":
        return f"point at {target}"
    if verb == "click":
        return f"click {target}"
    if verb == "type":
        return f"type {target}"
    return f"press {target}"


def authorize(verb: str, target: str) -> dict[str, Any]:
    """Ladder decision for one hands request, before anything touches the screen."""
    if verb not in VERBS:
        raise ValueError(f"unknown hands verb {verb!r}; use one of {', '.join(VERBS)}")
    if verb != "look" and not target.strip():
        raise ValueError(f"hands {verb} needs a target")
    decision = decide(describe(verb, target), hat="engineer")
    if decision["tier"] == TIER_REFUSE:
        decision["hands"] = {"verb": verb, "runs": False, "human_yes": "not asked: refused"}
        return decision
    if verb in OBSERVE_VERBS:
        # Looking and pointing write nothing; the ladder only gets to refuse them.
        if decision["tier"] != TIER_ACT:
            decision["downgraded"] = None
            decision["tier_from_words"] = decision["tier"]
            decision.update(tier=TIER_ACT, authority="act", mode="for",
                            reason="looking and pointing change nothing in the target app")
        decision["hands"] = {"verb": verb, "runs": True, "human_yes": "not needed: observe only"}
        return decision
    decision["hands"] = {"verb": verb, "runs": True,
                         "human_yes": "required: native 'Do it' dialog before acting"}
    return decision


def _not_run(reason: str, **extra: Any) -> dict[str, Any]:
    return {"ok": False, "status": "uncertain", "reason": reason, **extra}


def run(verb: str, target: str = "", *, index: int | None = None) -> dict[str, Any]:
    """Authorize, then (if allowed) call the helper. Returns the decision with a `result`."""
    decision = authorize(verb, target)
    if not decision["hands"]["runs"]:
        decision["result"] = _not_run("refused_by_ladder")
        return decision
    if sys.platform != "darwin":
        decision["result"] = _not_run("not_macos")
        return decision
    helper = helper_path()
    if not helper.is_file() or not os.access(helper, os.X_OK):
        decision["result"] = _not_run("helper_not_built", fix=f"run {BUILD_HINT} on the Mac")
        return decision

    argv = [str(helper), verb]
    if target:
        argv.append(target)
    if index is not None:
        argv += ["--index", str(index)]
    timeout = TIMEOUT_ACT_S if verb in ACT_VERBS else TIMEOUT_OBSERVE_S
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        decision["result"] = _not_run("helper_timed_out", timeout_s=timeout)
        return decision
    except OSError as exc:
        decision["result"] = _not_run("helper_failed_to_start", error=str(exc))
        return decision
    try:
        result = json.loads(proc.stdout.strip().splitlines()[-1])
    except (IndexError, ValueError):
        result = _not_run("helper_bad_output", exit_code=proc.returncode)
    if not isinstance(result, dict):
        result = _not_run("helper_bad_output", exit_code=proc.returncode)
    if result.get("status") == "confirmed":
        # Same-surface receipts never become confirmed (HONEST_CONTRACT rule 4).
        result["status"] = "attempted"
    decision["result"] = result
    return decision
