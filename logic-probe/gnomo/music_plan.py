"""MusicPlan: the structured musical intent between language and MIDI.

The third instance of the boring-schema pattern in this repo: the envelope
schema bounds probe claims, the decision ladder bounds companion authority,
this bounds composition. The LLM (or Chris) proposes a plan; nothing reaches
the compiler until it passes validation. The validator is deliberately
boring — that is the feature.

Deterministic boundary around probabilistic output:

    INTENT -> MUSIC PLAN -> validate -> MIDI COMPILER -> MELEGI aumi

Fail closed: an unknown chord symbol, meter, voicing, or register is an
error, never a guess. Absence of a rule is absence of permission.

Taste fields (voicing, register, velocity_range) are NOT invented here.
They carry the frozen defaults in DEFAULT_TASTE until Chris ratifies
others — studio/FAILURE_DRIVEN_ARCHITECTURE.md section 12. The compiler
never invents taste; it compiles ratified constants.
"""

from __future__ import annotations

import json
from typing import Any

# --- the boring tables (single source of truth; the compiler imports these) ---

TEMPO_MIN = 40
TEMPO_MAX = 220
BARS_MIN = 1
BARS_MAX = 32
VELOCITY_MIN = 1
VELOCITY_MAX = 127

# Recognized meters -> ticks per bar at 480 PPQ. Unknown meter = error.
METERS: dict[str, int] = {
    "4/4": 1920,
    "3/4": 1440,
}

# Recognized voicings / registers. Unknown = error, never a guess.
VOICINGS = frozenset({"closed", "wide", "shell"})
REGISTERS = frozenset({"low", "mid", "high"})
REGISTER_ROOT_OCTAVE = {"low": 2, "mid": 3, "high": 4}  # root octave, C-based

# Pitch classes, sharps preferred. Flats normalize to sharps.
PITCH_CLASS: dict[str, int] = {
    "c": 0, "c#": 1, "db": 1, "d": 2, "d#": 3, "eb": 3, "e": 4, "f": 5,
    "f#": 6, "gb": 6, "g": 7, "g#": 8, "ab": 8, "a": 9, "a#": 10, "bb": 10,
    "b": 11,
}

# Chord quality -> intervals in semitones from the root. Bounded and
# explicit; a symbol not here is an error. Recognized chord symbols only.
CHORD_INTERVALS: dict[str, tuple[int, ...]] = {
    "maj": (0, 4, 7),
    "min": (0, 3, 7),
    "dim": (0, 3, 6),
    "aug": (0, 4, 8),
    "7": (0, 4, 7, 10),
    "maj7": (0, 4, 7, 11),
    "min7": (0, 3, 7, 10),
    "m7b5": (0, 3, 6, 10),
    "6": (0, 4, 7, 9),
    "m6": (0, 3, 7, 9),
    "sus2": (0, 2, 7),
    "sus4": (0, 5, 7),
    "7sus4": (0, 5, 7, 10),
    "add9": (0, 4, 7, 14),
    "madd9": (0, 3, 7, 14),
    "9": (0, 4, 7, 10, 14),
    "maj9": (0, 4, 7, 11, 14),
    "m9": (0, 3, 7, 10, 14),
}

# Suffix spelling -> canonical quality key. Anything else is unrecognized.
QUALITY_ALIASES: dict[str, str] = {
    "": "maj", "m": "min", "min": "min", "-": "min", "dim": "dim", "o": "dim",
    "aug": "aug", "+": "aug", "7": "7", "maj7": "maj7", "ma7": "maj7",
    "m7": "min7", "min7": "min7", "-7": "min7", "m7b5": "m7b5",
    "6": "6", "m6": "m6", "-6": "m6", "sus2": "sus2", "sus4": "sus4",
    "sus": "sus4", "7sus4": "7sus4", "7sus": "7sus4", "add9": "add9",
    "madd9": "madd9", "9": "9", "maj9": "maj9", "m9": "m9", "-9": "m9",
}

# Frozen taste defaults — Chris ratifies; the compiler compiles, never invents.
DEFAULT_TASTE: dict[str, Any] = {
    "voicing": "closed",
    "register": "mid",
    "velocity_range": [64, 96],
}


class MusicPlanError(ValueError):
    """The plan did not pass validation. Nothing downstream may run."""


def parse_chord(symbol: str) -> tuple[int, str]:
    """'Bbmaj7' -> (root pitch class 10, quality 'maj7'). Unknown = error."""
    s = symbol.strip()
    if not s:
        raise MusicPlanError("empty chord symbol")
    low = s.lower()
    # Root: one letter, plus an accidental when the pair is a known PC.
    i = 1
    if len(low) > 1 and low[1] in "#b" and low[:2] in PITCH_CLASS:
        i = 2
    root_part = low[:i]
    if root_part not in PITCH_CLASS:
        raise MusicPlanError(f"unrecognized chord root: {symbol!r}")
    root_pc = PITCH_CLASS[root_part]
    rest = low[i:]
    quality = QUALITY_ALIASES.get(rest)
    if quality is None:
        raise MusicPlanError(f"unrecognized chord quality: {symbol!r}")
    return root_pc, quality


def chord_notes(symbol: str) -> tuple[int, ...]:
    """Pitch-class intervals for one chord symbol. Same table as the compiler."""
    root_pc, quality = parse_chord(symbol)
    return tuple(sorted({(root_pc + iv) % 12 for iv in CHORD_INTERVALS[quality]}))


def validate_plan(raw: Any) -> dict[str, Any]:
    """Validate one raw dict into a canonical plan, or raise MusicPlanError.

    Fills frozen defaults for taste fields (explicitly marked `defaulted`),
    normalizes chords through the recognized table, and rejects anything
    out of range. The output is what the compiler is allowed to see.
    """
    if not isinstance(raw, dict):
        raise MusicPlanError("plan must be a JSON object")
    errors: list[str] = []
    plan: dict[str, Any] = {}

    tempo = raw.get("tempo")
    if not isinstance(tempo, int) or isinstance(tempo, bool) or not (TEMPO_MIN <= tempo <= TEMPO_MAX):
        errors.append(f"tempo must be int {TEMPO_MIN}..{TEMPO_MAX}, got {tempo!r}")
    else:
        plan["tempo"] = tempo

    meter = raw.get("meter", "4/4")
    if meter not in METERS:
        errors.append(f"meter must be one of {sorted(METERS)}, got {meter!r}")
    else:
        plan["meter"] = meter

    bars = raw.get("length_bars")
    if not isinstance(bars, int) or isinstance(bars, bool) or not (BARS_MIN <= bars <= BARS_MAX):
        errors.append(f"length_bars must be int {BARS_MIN}..{BARS_MAX}, got {bars!r}")
    else:
        plan["length_bars"] = bars

    chords = raw.get("chords")
    if not isinstance(chords, list) or not chords:
        errors.append("chords must be a non-empty list of chord symbols")
    else:
        if isinstance(bars, int) and len(chords) != bars:
            errors.append(f"chords ({len(chords)}) must fill length_bars ({bars})")
        checked: list[str] = []
        for sym in chords:
            if not isinstance(sym, str):
                errors.append(f"chord symbol must be a string, got {sym!r}")
                continue
            try:
                parse_chord(sym)
                checked.append(sym.strip())
            except MusicPlanError as exc:
                errors.append(str(exc))
        plan["chords"] = checked

    for field, allowed in (("voicing", VOICINGS), ("register", REGISTERS)):
        value = raw.get(field)
        if value is None:
            plan[field] = DEFAULT_TASTE[field]
            plan[f"{field}_defaulted"] = True
        elif value in allowed:
            plan[field] = value
        else:
            errors.append(f"{field} must be one of {sorted(allowed)}, got {value!r}")

    vr = raw.get("velocity_range")
    if vr is None:
        plan["velocity_range"] = list(DEFAULT_TASTE["velocity_range"])
        plan["velocity_range_defaulted"] = True
    elif (
        isinstance(vr, list)
        and len(vr) == 2
        and all(isinstance(v, int) and not isinstance(v, bool) for v in vr)
        and VELOCITY_MIN <= vr[0] <= vr[1] <= VELOCITY_MAX
    ):
        plan["velocity_range"] = vr
    else:
        errors.append(f"velocity_range must be [lo, hi] within {VELOCITY_MIN}..{VELOCITY_MAX}, got {vr!r}")

    key = raw.get("key")
    if key is not None:
        if isinstance(key, str) and _known_key(key):
            plan["key"] = key.strip()
        else:
            errors.append(f"unrecognized key: {key!r} (use e.g. 'D minor', 'C major')")

    from .melody import validate_melody

    melody = raw.get("melody")
    if melody is not None:
        try:
            plan["melody"] = validate_melody(melody)
        except MusicPlanError as exc:
            errors.append(str(exc))

    if errors:
        raise MusicPlanError("; ".join(errors))
    return plan


_MAJOR = ("major", "maj")
_MINOR = ("minor", "min", "m")


def _known_key(key: str) -> bool:
    k = key.strip().lower()
    for note in PITCH_CLASS:
        if k.startswith(note + " ") or k == note:
            tail = k[len(note):].strip()
            if not tail:
                return True  # bare note = major by convention
            return tail in _MAJOR or tail in _MINOR
    return False


def plan_from_json(text: str) -> dict[str, Any]:
    """Parse + validate JSON text. Raises MusicPlanError (json or schema)."""
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise MusicPlanError(f"plan is not valid JSON: {exc}") from exc
    return validate_plan(raw)


def load_plan(path: str) -> dict[str, Any]:
    """Load + validate a plan file."""
    from pathlib import Path

    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise MusicPlanError(f"cannot read plan file: {exc}") from exc
    return plan_from_json(text)