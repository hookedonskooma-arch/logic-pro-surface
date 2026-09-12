"""Melody layer: bounded, deterministic melodic realization over the chords.

Composition ladder v0.2 (studio/FAILURE_DRIVEN_ARCHITECTURE.md: v0.2 =
TEXT -> CHORDS + MELODY). Doctrine, unchanged from the chord layer:

- The LLM stops at the plan. A `melody` block in the MusicPlan carries
  taste RATIFIED BY CHRIS (style + density + register) — the compiler
  never invents taste, it compiles ratified constants.
- Everything is tables. An unknown style, density, or a note the rules
  cannot place is an error, never a guess. Fail closed, like the
  validator: absence of a rule is absence of permission.
- Determinism contract: same plan -> same melody events, byte for byte.
  The melody walks a fixed, testable path through the chord tones.

Musical law baked in (not taste, physics of the vocabulary):
- melody notes come from the underlying chord's pitch classes
  (chord-tone approach: every melody note IS a chord tone in its bar —
  the recognized table has no passing tones; that is the bound)
- melody register sits above the chord voicing's root by construction
- rhythm comes from the density table, not randomness

Styles (bounded set, one meaning each):
  arpeggio  — chord tones ascending, one per beat slot, looped
  anthem    — sustained: root+fifth long tones, hymn-like, one per bar
  riff      — chord tones in a fixed descending-then-root pattern
  lead      — top voice of the voicing, held for the bar's second half

Density slots per bar (4/4; 3/4 scales): sparse=2, steady=4, busy=8.
The melodic octave is register + 1 (above the chord stack).
"""

from __future__ import annotations

from typing import Any

from .music_plan import CHORD_INTERVALS, MusicPlanError, parse_chord

# Bounded taste tables — Chris ratifies, the compiler compiles.
MELODY_STYLES = frozenset({"anthem", "riff", "lead"})
MELODY_DENSITY = frozenset({"sparse", "steady", "busy"})
# slots per bar in 4/4; 3/4 uses ceil(slots * 3/4)
DENSITY_SLOTS = {"sparse": 2, "steady": 4, "busy": 8}

# Registers the melody may live in (octave above the chord register).
MELODY_REGISTER_SHIFT = {"low": 1, "mid": 1, "high": 1}  # always one octave up


def validate_melody(raw: Any) -> dict[str, Any] | None:
    """Validate the plan's optional melody block into canonical form.

    Absent block -> None (chords-only plan, v0.1 behavior unchanged).
    Present block: style + density required, both from closed sets.
    register inherits the chord register unless explicitly given here.
    """
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise MusicPlanError("melody must be an object with style + density")
    errors: list[str] = []

    style = raw.get("style")
    if style not in MELODY_STYLES:
        errors.append(f"melody.style must be one of {sorted(MELODY_STYLES)}, got {style!r}")

    density = raw.get("density")
    if density not in MELODY_DENSITY:
        errors.append(f"melody.density must be one of {sorted(MELODY_DENSITY)}, got {density!r}")

    register = raw.get("register")
    if register is not None and register not in ("low", "mid", "high"):
        errors.append(f"melody.register must be one of ['high', 'low', 'mid'], got {register!r}")

    if errors:
        raise MusicPlanError("; ".join(errors))
    out: dict[str, Any] = {"style": style, "density": density}
    if register is not None:
        out["register"] = register
    return out


def _slots_for(density: str, meter: str) -> int:
    """Rhythm slots this bar. Deterministic: same density+meter, same slots."""
    base = DENSITY_SLOTS[density]
    if meter == "3/4":
        # three quarter notes per bar: keep the grid musical, never fractional
        return max(1, round(base * 3 / 4))
    return base


def _melody_pitch_sequence(symbol: str, style: str, slots: int, base_midi: int) -> list[int]:
    """The fixed pitch pattern for one bar. Same inputs, same notes, always.

    base_midi is the melody root (chord root pitched in the melody octave).
    Every note is a chord tone: intervals come from the recognized table.
    """
    root_pc, quality = parse_chord(symbol)
    intervals = CHORD_INTERVALS[quality]

    def tone(i: int) -> int:
        return base_midi + intervals[i % len(intervals)]

    if style == "anthem":
        # one long tone per slot: root, then fifth alternation
        return [base_midi if i % 2 == 0 else tone(2) for i in range(slots)]
    if style == "riff":
        # descend from the top extension to the root, then climb back one
        seq = list(range(len(intervals) - 1, -1, -1))
        out = []
        for i in range(slots):
            idx = seq[i % len(seq)] if (i % len(seq)) != len(seq) - 1 or i < slots else 0
            out.append(tone(idx))
        return out
    if style == "lead":
        # top voice held: the highest extension, repeated (sustained lead)
        return [tone(len(intervals) - 1)] * slots
    raise MusicPlanError(f"unrecognized melody style: {style!r}")  # unreachable


def compile_melody(plan: dict[str, Any], ticks_per_bar: int) -> list[dict[str, Any]]:
    """Melody bars -> event structure, same shape as the chord bars.

    Melody register = chord register + 1 octave, so the line floats above
    the stack without colliding. Velocity reuses the plan's frozen range
    via the same spread rules (root/strong slots get the top of the range).
    """
    melody = plan.get("melody")
    if not melody:
        return []
    style = melody["style"]
    register = melody.get("register", plan["register"])
    lo, hi = plan["velocity_range"]

    from .music_plan import REGISTER_ROOT_OCTAVE

    root_octave = REGISTER_ROOT_OCTAVE[register] + MELODY_REGISTER_SHIFT[register]
    slots = _slots_for(melody["density"], plan["meter"])
    slot_ticks = ticks_per_bar // slots

    bars: list[dict[str, Any]] = []
    for i, sym in enumerate(plan["chords"]):
        root_pc, _quality = parse_chord(sym)
        # melody root = this chord's root, one octave above the chord stack's
        # root octave. Every pitch is then root-relative from the same table.
        base_midi = 12 * (root_octave + 1) + root_pc
        pitches = _melody_pitch_sequence(sym, style, slots, base_midi)
        # deterministic velocity: strong slots (beat 0 and mid-bar) high,
        # offbeats lower; bounded to the ratified range.
        mid = (lo + hi) // 2
        velos = []
        for s in range(slots):
            velos.append(hi if s == 0 else (mid if s % 2 == 0 else mid + 1))
        notes = [
            {"note": p, "velocity": max(lo, min(hi, v))}
            for p, v in zip(pitches, velos)
        ]
        bars.append(
            {
                "bar": i + 1,
                "symbol": sym,
                "start_tick": i * ticks_per_bar,
                "end_tick": (i + 1) * ticks_per_bar,
                "notes": notes,
                "voice": "melody",
            }
        )
    return bars


def weave_events(compiled: dict[str, Any], melody_bars: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge melody bars into the compiled structure for SMF + hash + send.

    The hash extends deterministically: chord notes first (voice absent =
    chord), then melody notes in bar order, so v0.1 hashes stay valid and
    v0.2 phrases hash differently from their chord-only skeleton.
    """
    import hashlib

    compiled = dict(compiled)
    compiled["melody_bars"] = melody_bars
    parts: list[str] = []
    for bar in compiled["bars"]:
        for entry in bar["notes"]:
            parts.append(f"{bar['start_tick']}:{entry['note']}:{entry['velocity']}")
    for bar in melody_bars:
        for entry in bar["notes"]:
            parts.append(f"m{bar['start_tick']}:{entry['note']}:{entry['velocity']}")
    blob = "|".join(parts) + f"|ppq{compiled['ppq']}"
    compiled["phrase_hash"] = hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]
    compiled["event_count"] = sum(
        len(b["notes"]) * 2 for b in compiled["bars"]
    ) + sum(len(b["notes"]) * 2 for b in melody_bars)
    return compiled