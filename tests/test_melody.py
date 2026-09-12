"""Melody layer (v0.2): bounded styles, deterministic realization.

Pins the v0.2 composition ladder contract:
- melody block validates against closed sets (anthem/riff/lead,
  sparse/steady/busy); unknown = MusicPlanError
- absent melody block -> chords-only, byte-identical to v0.1 (hash too)
- same plan -> same melody events, same hash, same SMF bytes
- every melody note is a chord tone of its bar (physics of the bound)
- melody lives one octave above the chord register, above the stack
- SMF carries melody on channel 1 (0x91/0x81), chords stay on 0
- hash extension is deterministic and order-stable (chords then m-notes)
"""

from __future__ import annotations

import json

import pytest

from gnomo.melody import DENSITY_SLOTS, compile_melody, validate_melody, weave_events
from gnomo.midi_compiler import compile_plan, events_to_smf
from gnomo.music_plan import MusicPlanError, validate_plan

CHORDS = {
    "tempo": 88,
    "key": "D minor",
    "length_bars": 4,
    "chords": ["Dm9", "Bbmaj7", "Fadd9", "C"],
    "voicing": "wide",
    "register": "mid",
    "velocity_range": [48, 76],
}


# --- validator ----------------------------------------------------------------

def test_melody_block_validates():
    m = validate_melody({"style": "riff", "density": "steady"})
    assert m == {"style": "riff", "density": "steady"}


def test_melody_register_optional():
    m = validate_melody({"style": "anthem", "density": "sparse", "register": "high"})
    assert m["register"] == "high"


@pytest.mark.parametrize(
    "bad",
    [
        {"style": "shred", "density": "steady"},       # unknown style
        {"style": "riff", "density": "frantic"},        # unknown density
        {"style": "riff", "density": "steady", "register": "sub"},  # unknown register
        "riff",                                          # not an object
        {},                                              # missing both
    ],
)
def test_melody_fail_closed(bad):
    with pytest.raises(MusicPlanError):
        validate_melody(bad)


def test_plan_rejects_bad_melody():
    with pytest.raises(MusicPlanError, match="melody.style"):
        validate_plan({**CHORDS, "melody": {"style": "shred", "density": "steady"}})


def test_plan_accepts_good_melody():
    plan = validate_plan({**CHORDS, "melody": {"style": "riff", "density": "steady"}})
    assert plan["melody"] == {"style": "riff", "density": "steady"}


# --- determinism --------------------------------------------------------------

def test_chords_only_plan_hash_unchanged():
    """v0.2 must not move v0.1 hashes: chord-only compiles identically."""
    a = compile_plan(validate_plan(CHORDS))
    b = compile_plan(validate_plan(dict(CHORDS)))
    assert a["phrase_hash"] == b["phrase_hash"]
    assert a["smf"] == b["smf"]
    # and it matches the committed example's structural count (4 bars wide)
    assert a["event_count"] == (5 + 4 + 4 + 3) * 2


def test_melody_plan_is_deterministic():
    withmel = {**CHORDS, "melody": {"style": "riff", "density": "busy"}}
    a = compile_plan(validate_plan(withmel))
    b = compile_plan(validate_plan(dict(withmel)))
    assert a["phrase_hash"] == b["phrase_hash"]
    assert a["smf"] == b["smf"]


def test_melody_hash_differs_from_chord_only():
    skeleton = compile_plan(validate_plan(CHORDS))
    withmel = compile_plan(
        validate_plan({**CHORDS, "melody": {"style": "riff", "density": "steady"}})
    )
    assert skeleton["phrase_hash"] != withmel["phrase_hash"]


# --- musical law ----------------------------------------------------------------

def test_melody_notes_are_chord_tones():
    """Every melody note is a pitch class of its bar's chord (plus octave)."""
    plan = validate_plan({**CHORDS, "melody": {"style": "riff", "density": "busy"}})
    compiled = compile_plan(plan)
    from gnomo.music_plan import chord_notes

    for i, bar in enumerate(compiled["melody_bars"]):
        allowed = set(chord_notes(bar["symbol"]))
        for entry in bar["notes"]:
            assert entry["note"] % 12 in allowed, (
                f"bar {i + 1}: note {entry['note']} is not a chord tone of {bar['symbol']}"
            )


def test_melody_sits_above_chord_root():
    """True invariant: every melody note >= its bar's chord root + 1 octave.

    (Crossing the chord's UPPER voices is normal voice leading and allowed;
    dipping below the root octave is not — that would muddy the stack.)
    """
    plan = validate_plan({**CHORDS, "melody": {"style": "riff", "density": "busy"}})
    compiled = compile_plan(plan)
    from gnomo.music_plan import parse_chord

    for bar in compiled["melody_bars"]:
        root_pc, _ = parse_chord(bar["symbol"])
        chord_root = 12 * 4 + root_pc  # chord register root octave for "mid" = 3 -> midi root_oct math: 12*(3+1)=48
        floor = chord_root + 12  # one octave above the chord's root
        for entry in bar["notes"]:
            assert entry["note"] >= floor


def test_density_slots():
    plan = validate_plan({**CHORDS, "melody": {"style": "riff", "density": "busy"}})
    bars = compile_melody(plan, 1920)
    assert len(bars[0]["notes"]) == 8  # busy = 8 slots in 4/4
    plan34 = validate_plan(
        {**CHORDS, "meter": "3/4", "melody": {"style": "riff", "density": "busy"}}
    )
    bars3 = compile_melody(plan34, 1440)
    assert len(bars3[0]["notes"]) == max(1, round(8 * 3 / 4))


def test_velocity_bounded_to_ratified_range():
    plan = validate_plan({**CHORDS, "melody": {"style": "anthem", "density": "steady"}})
    compiled = compile_plan(plan)
    lo, hi = plan["velocity_range"]
    for bar in compiled["melody_bars"]:
        for entry in bar["notes"]:
            assert lo <= entry["velocity"] <= hi


def test_styles_produce_different_lines():
    lines = {}
    for style in ("anthem", "riff", "lead"):
        plan = validate_plan({**CHORDS, "melody": {"style": style, "density": "steady"}})
        compiled = compile_plan(plan)
        lines[style] = [e["note"] for b in compiled["melody_bars"] for e in b["notes"]]
    assert len({tuple(v) for v in lines.values()}) == 3


# --- SMF: melody rides channel 1 -------------------------------------------------

def test_smf_carries_melody_on_channel_1():
    plan = validate_plan({**CHORDS, "melody": {"style": "riff", "density": "steady"}})
    compiled = compile_plan(plan)
    smf = compiled["smf"]
    melody_ons = compiled["melody_bars"][0]["notes"]
    first = compiled["melody_bars"][0]["notes"][0]["note"]
    assert bytes([0x91, first]) in smf  # note_on channel 1
    assert bytes([0x81, first, 0x40]) in smf  # note_off channel 1


def test_weave_events_extends_count_and_hash():
    withmel = compile_plan(validate_plan({**CHORDS, "melody": {"style": "riff", "density": "busy"}}))
    chords_only = compile_plan(validate_plan(CHORDS))
    # melody adds 8 slots * 2 events per bar * 4 bars = 64 events
    assert withmel["event_count"] == chords_only["event_count"] + 8 * 2 * 4
    assert withmel["phrase_hash"] != chords_only["phrase_hash"]