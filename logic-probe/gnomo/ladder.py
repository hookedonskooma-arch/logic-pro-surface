"""The decision ladder: does GNOMO act FOR you, WITH you, or hand it back?

This is the honest contract expressed as *authority* instead of *status*.
docs/HONEST_CONTRACT.md says what may be called confirmed. This says what may
be done without asking. Same rules, other axis.

Fail-closed default: an action that matches no rule is tier 2 (ask). An
unrecognised action is never permission to act.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

TIER_ACT = 0
TIER_PROPOSE = 1
TIER_ASK = 2
TIER_REFUSE = 3

_AUTHORITY = {
    TIER_ACT: ("act", "for"),
    TIER_PROPOSE: ("propose", "with"),
    TIER_ASK: ("ask", "you"),
    TIER_REFUSE: ("refuse", "never"),
}

TIER_MEANING = {
    TIER_ACT: "reversible, verifiable, writes nothing into a Logic project",
    TIER_PROPOSE: "reversible in Logic with a stated rollback; runs on one nod",
    TIER_ASK: "taste, UNKNOWN tag, or no rollback; the human decides",
    TIER_REFUSE: "the gnome does not do this, and does not negotiate about it",
}


class Rule:
    """One ladder rung. `rollback` is mandatory for tier 1 and must be real."""

    def __init__(
        self,
        *,
        tier: int,
        pattern: str,
        reason: str,
        rollback: str | None = None,
        needs: tuple[str, ...] = (),
        also: str | None = None,
        unless: str | None = None,
    ) -> None:
        self.tier = tier
        self.pattern = re.compile(pattern, re.IGNORECASE)
        self.reason = reason
        self.rollback = rollback
        self.needs = needs
        # `also` must match too; `unless` disqualifies the rung. Together they
        # let a rung turn on what is being acted upon, not just the verb.
        self.also = re.compile(also, re.IGNORECASE) if also else None
        self.unless = re.compile(unless, re.IGNORECASE) if unless else None

    def matches(self, action: str) -> bool:
        if not self.pattern.search(action):
            return False
        if self.also is not None and not self.also.search(action):
            return False
        if self.unless is not None and self.unless.search(action):
            return False
        return True


# Hearing the human is not hearing the mix. The line is drawn by OBJECT, not
# by verb: "listen" is not the dangerous word, what is being listened to is.
# The ears vocabulary, defined once. The tier-3 refusal below uses it, and the
# allow rung uses it as a guard - so widening one can never silently widen the
# other. A transcription ask that also asks "is it good" is a judgement ask.
EARS = (
    r"\b(hear|hearing|heard|listen(ed|ing|s)?|audition|ears?)\b"
    r"|\bsound(s|ed|ing)?\b"
    r"|\b(better|worse|good|bad)\b"
)

TRANSCRIBE = (
    r"\b(transcribe|transcription|dictate|dictation|speech[-\s]?to[-\s]?text"
    r"|voice (note|memo)|note this down|what did i (just )?say|stt)\b"
)

# Name any of these and it is audio analysis, not taking down your words.
MUSICAL_OBJECT = (
    # "take" only as a noun: "the take", "vocal take" - never the verb in
    # "take a voice note", which is the whole point of the allow rung.
    r"\b(?:the|that|this|a|another|second|third|last|first|vocal|guitar|drum)\s+takes?\b"
    r"|\b(mix|mixes|track|tracks|stems?|regions?|songs?|beats?|master"
    r"|bus|buses|vocals?|guitars?|bass|drums?|snare|kick|hats?|808s?|synths?"
    r"|riffs?|tone|eq|reverb|compressor|loudness|lufs|arrangement)\b"
)

# Order is authority order: REFUSE is checked first, ACT last. A phrase that
# trips a refusal never falls through to a softer rung.
RULES: tuple[Rule, ...] = (
    # --- the hearing line: your voice, never the mix -----------------------
    # Deliberately narrow, and it fails closed: transcription intent AND no
    # musical object named. Miss either half and it drops to the twin below.
    Rule(
        tier=TIER_ACT,
        pattern=TRANSCRIBE,
        unless=f"{MUSICAL_OBJECT}|{EARS}",
        reason=(
            "transcribing your speech is not metering audio; it returns text, "
            "never a judgement about how anything sounds"
        ),
    ),
    Rule(
        tier=TIER_REFUSE,
        pattern=TRANSCRIBE,
        also=MUSICAL_OBJECT,
        reason=(
            "transcribing a musical object is audio analysis, not taking down "
            "your words; this layer still has no ears for the mix"
        ),
    ),

    # --- tier 3: never -----------------------------------------------------
    Rule(
        tier=TIER_REFUSE,
        # Deliberately wide. "Check how the guitar sounds" is a hearing request
        # wearing a read's clothes, and a read is tier 0. A false refusal costs
        # one sentence; a false ACT ships the exact lie this repo was built to
        # stop. Any judgement of sound is a no, however it is phrased.
        pattern=EARS,
        reason="this layer has no ears; claiming a listen is the lie the repo exists to stop",
    ),
    Rule(
        tier=TIER_REFUSE,
        pattern=r"\b(ax|accessibility)\b.*\b(confirm|verified|truth|proof)\b",
        reason="AX is a UI receipt, not musical truth (HONEST_CONTRACT rule 4)",
    ),
    Rule(
        tier=TIER_REFUSE,
        pattern=r"\brebuild defaults\b",
        reason="Rebuild Defaults would wipe the iPad Logic Remote assignment",
    ),
    Rule(
        tier=TIER_REFUSE,
        pattern=r"\bmelegi\b.*\b(audio|bus|buses|pass-?through|mixer|synth|mouth|tts)\b",
        reason="MELEGI is aumi MIDI FX only (Decision 001). It is not the mouth and not a mixer",
    ),
    Rule(
        tier=TIER_REFUSE,
        pattern=r"\b(logic remote|ipad)\b.*\b(assign|reassign|remove|change)\b",
        reason="the iPad Logic Remote assignment is on the DO NOT TOUCH list",
    ),
    Rule(
        tier=TIER_REFUSE,
        pattern=r"\b(invent|guess|assume|make up|fake)\b.*\b(state|track|tempo|loudness|db|project)\b",
        reason="never invent Logic state (HONEST_CONTRACT rule 6); null and say why",
    ),
    Rule(
        tier=TIER_REFUSE,
        pattern=r"\b(mark|promote|call|tag)\b.*\b(verified|tested|confirmed|supported)\b",
        reason="a tag is earned by evidence, not by a companion feeling good about it",
    ),

    # --- tier 2: the human decides ----------------------------------------
    Rule(
        tier=TIER_ASK,
        pattern=r"\b(distortion|room|doubles?|human timing|autotune|vibe|feel|taste)\b",
        reason="TASTE_PROFILE protects this; Chris is creative director",
        needs=("taste call",),
    ),
    Rule(
        tier=TIER_ASK,
        pattern=r"\b(arrange|arrangement|structure|song order|verse|chorus|bridge)\b",
        reason="arrangement is a taste call, not a probe",
        needs=("taste call",),
    ),
    Rule(
        tier=TIER_ASK,
        pattern=r"\b(master|mastering|loudness|lufs|limiter|ceiling)\b",
        reason="we cannot meter loudness (MCP_CAPABILITIES: unchecked). No ears, no master",
        needs=("a metering capability we do not have",),
    ),
    Rule(
        tier=TIER_ASK,
        pattern=r"\b(delete|erase|overwrite|bounce over|replace|wipe|flatten)\b",
        reason="destructive and not rollback-able from here (HONEST_CONTRACT rule 8)",
        needs=("a checkpointed copy of the project",),
    ),
    Rule(
        tier=TIER_ASK,
        pattern=r"\b(control surfaces?|setup|preferences)\b.*\b(assign|mackie)\b",
        reason="control-surface setup is a hands-on Logic step; the gnome cannot click it honestly",
        needs=("Chris at the Mac",),
    ),
    Rule(
        tier=TIER_ASK,
        pattern=r"\b(ship|release|publish|post|tweet|upload)\b",
        reason="anything leaving the machine is the human's call",
        needs=("explicit go",),
    ),

    # --- tier 1: with you, one nod, stated rollback ------------------------
    Rule(
        tier=TIER_PROPOSE,
        pattern=r"\b(fader|volume|set-volume|-?\d+\s*db|gain)\b",
        reason="MCU fader move; reversible and independently checkable by MCU echo",
        rollback="write the captured `before` dB back to the same fader",
        needs=("Mackie Control assigned to the IAC ports (PROJECT_STATE blocker)",),
    ),
    Rule(
        tier=TIER_PROPOSE,
        pattern=r"\b(transport|play|stop|record|rewind|locate)\b",
        reason="transport is reversible; MCU echo can confirm it",
        rollback="stop transport and return the playhead to its captured position",
        needs=("Mackie Control assigned to the IAC ports (PROJECT_STATE blocker)",),
    ),
    Rule(
        tier=TIER_PROPOSE,
        pattern=r"\b(insert|instantiate|load)\b.*\b(scripter|midi fx|aumi|au|plug-?in)\b",
        reason="an insert on a scratch track is reversible by removing the slot",
        rollback="remove the plug-in from the slot it was inserted into",
        needs=("a scratch track, never the user's only project",),
    ),
    Rule(
        tier=TIER_PROPOSE,
        pattern=r"\b(mute|solo|pan|send|bank|select track)\b",
        reason="mixer toggle over MCU; reversible and echo-checkable",
        rollback="restore the captured `before` value on the same strip",
        needs=("Mackie Control assigned to the IAC ports (PROJECT_STATE blocker)",),
    ),

    # --- tier 0: for you ---------------------------------------------------
    Rule(
        tier=TIER_ACT,
        pattern=r"\b(probes?|envelopes?|status|reads?|inspect|list|checks?|shows?|reports?)\b",
        reason="read-only probe; prints an envelope and writes nothing into Logic",
    ),
    Rule(
        tier=TIER_ACT,
        pattern=r"\b(parks?|captures?|notes?|logs?|remember|write down)\b",
        reason="capturing an idea costs nothing and loses nothing",
    ),
    Rule(
        tier=TIER_ACT,
        pattern=r"\b(tests?|pytest|lint|ci|builds?|compiles?)\b",
        reason="repo-local and reversible by git; touches no session",
    ),
    Rule(
        tier=TIER_ACT,
        pattern=r"\b(say|speak|announce|remind)\b",
        reason="speaking is free and changes nothing",
    ),
    Rule(
        tier=TIER_ACT,
        pattern=r"\b(next|what now|one thing|focus)\b",
        reason="picking the one next thing is the gnome's whole job",
    ),
)

DEFAULT_REASON = (
    "no ladder rule matched, so the gnome will not assume permission "
    "(unknown is not a yes)"
)


def _utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def classify(action: str) -> Rule | None:
    """First matching rule in authority order, or None for the fail-closed default."""
    for rule in RULES:
        if rule.matches(action):
            return rule
    return None


def decide(
    action: str,
    *,
    hat: str = "engineer",
    blockers: tuple[str, ...] = (),
    grounded_in: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Return one decision. Never two. Never a maybe.

    A tier-1 rule with no rollback is downgraded to tier 2: if we cannot undo
    it, it is not ours to start.
    """
    action = action.strip()
    if not action:
        raise ValueError("decide() needs an action; the gnome does not guess the ask")

    rule = classify(action)
    if rule is None:
        tier, reason, rollback, needs = TIER_ASK, DEFAULT_REASON, None, ("a clearer ask",)
    else:
        tier, reason, rollback, needs = rule.tier, rule.reason, rule.rollback, rule.needs

    downgraded = None
    if tier == TIER_PROPOSE and not rollback:
        tier = TIER_ASK
        downgraded = "tier 1 without a stated rollback is not actionable; handed back"

    authority, mode = _AUTHORITY[tier]
    return {
        "companion": "GNOMO",
        "timestamp": _utc_now_iso(),
        "hat": hat,
        "action": action,
        "tier": tier,
        "authority": authority,
        "mode": mode,
        "meaning": TIER_MEANING[tier],
        "reason": reason,
        "rollback": rollback,
        "needs": list(needs),
        "blockers": list(blockers),
        "grounded_in": list(grounded_in),
        "downgraded": downgraded,
    }
