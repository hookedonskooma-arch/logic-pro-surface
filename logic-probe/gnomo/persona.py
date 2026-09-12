"""The gnome's voice. One mouth, one action, no flattery.

Speech rules, in order:

1. **One thing.** Every turn names exactly one action. Extra ideas go to the
   parking lot, they do not go in the sentence. This is the ADHD contract:
   the gnome is the thing that holds the other nine ideas so the hands can
   finish this one.
2. **Authority first.** The first words say who is deciding, so the human
   never has to reverse-engineer whether they were just told or just asked.
3. **Short.** This is TTS. Two sentences maximum. A paragraph read aloud is
   a paragraph nobody hears.
4. **No hype.** The gnome is old, small, and sits on the desk. It does not
   congratulate, it does not say "great question", it does not narrate its
   own helpfulness.
5. **Never claim ears.** No "sounds good". It has none.
"""

from __future__ import annotations

import re
from typing import Any

from .ladder import TIER_ACT, TIER_ASK, TIER_PROPOSE, TIER_REFUSE

OPENERS = {
    TIER_ACT: "Doing it.",
    TIER_PROPOSE: "Say the word.",
    TIER_ASK: "Your call.",
    TIER_REFUSE: "No.",
}

# Markdown is for the eye; the mouth should not read backticks and asterisks.
# Underscores are left alone: MCP_CAPABILITIES must not become MCPCAPABILITIES.
_MARKUP = re.compile(r"[`*#>]+")
_WS = re.compile(r"\s+")


def plain(text: str) -> str:
    return _WS.sub(" ", _MARKUP.sub("", text)).strip()


def _first_sentence(text: str, limit: int = 120) -> str:
    """One sentence, no trailing stop, first letter raised.

    The caller supplies the punctuation, so clauses never come out doubled.
    """
    text = plain(text)
    head = re.split(r"(?<=[.!?])\s", text, maxsplit=1)[0]
    if len(head) > limit:
        head = head[: limit - 1].rstrip() + "\u2026"
    head = head.rstrip(" .;,")
    if head[:1].islower():
        head = head[0].upper() + head[1:]
    return head


def line(decision: dict[str, Any]) -> str:
    """One spoken line for one decision. Two sentences, hard ceiling."""
    tier = decision["tier"]
    opener = OPENERS[tier]
    action = _first_sentence(decision["action"], limit=90)

    if tier == TIER_ACT:
        return f"{opener} {action}."
    if tier == TIER_PROPOSE:
        blocked = decision.get("blockers") or []
        if blocked:
            return f"{opener} {action}, once this clears: {_first_sentence(blocked[0], limit=70)}."
        return f"{opener} {action}. I can undo it: {_first_sentence(decision['rollback'], limit=70)}."
    if tier == TIER_ASK:
        return f"{opener} {action}. {_first_sentence(decision['reason'], limit=90)}."
    if tier == TIER_REFUSE:
        return f"{opener} {_first_sentence(decision['reason'], limit=110)}."
    raise ValueError(f"unknown tier: {tier!r}")


def brief(snapshot: dict[str, Any], decision: dict[str, Any] | None = None) -> str:
    """The 'what now' line. One thing, then the one blocker in its way."""
    now = snapshot.get("now")
    if not now:
        return (
            "No NOW item in the studio notes, so I am not inventing one. "
            "Tell me the one thing and I will hold the rest."
        )
    said = f"One thing: {_first_sentence(now, limit=110)}."
    blockers = snapshot.get("blockers") or []
    if blockers:
        said += f" Blocked on: {_first_sentence(blockers[0], limit=90)}."
    elif decision is not None:
        said += f" {OPENERS[decision['tier']]}"
    return said


def hat_line(hat: str) -> str:
    """Roles are hats, announced, not separate speakers."""
    return f"GNOMO, {hat} hat."
