"""MusicPlan validator + deterministic MIDI compiler: the boring boundary.

These tests pin the composition seam's machine half before it ever touches
Logic: same plan -> same bytes, unknowns fail closed, taste comes only from
frozen fields, and the SMF is structurally real (parseable by mido when it
is installed; structurally checked here without it).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gnomo.midi_compiler import (
    _varlen,
    compile_events,
    compile_plan,
    events_to_smf,
    phrase_hash,
    write_smf,
)
from gnomo.music_plan import (
    DEFAULT_TASTE,
    MusicPlanError,
    chord_notes,
    parse_chord,
    plan_from_json,
    validate_plan,
)

# The doc's own example (studio/FAILURE_DRIVEN_ARCHITECTURE.md section 3).
SHOEGAZE_PLAN = {
    "tempo": 88,
    "key": "D minor",
    "length_bars": 8,
    "chords": ["Dm9", "Bbmaj7", "Fadd9", "C", "Dm9", "Bbmaj7", "Gm9", "A7sus4"],
    "voicing": "wide",
    "register": "mid",
    "velocity_range": [48, 76],
}


# --- validator ---------------------------------------------------------------

def test_doc_example_plan_validates():
    plan = validate_plan(SHOEGAZE_PLAN)
    assert plan["tempo"] == 88
    assert plan["meter"] == "4/4"
    assert plan["chords"] == SHOEGAZE_PLAN["chords"]
    assert plan["voicing"] == "wide" and plan["register"] == "mid"
    assert plan["velocity_range"] == [48, 76]
    # explicit fields are not marked defaulted
    assert "voicing_defaulted" not in plan


def test_taste_defaults_fill_and_mark():
    plan = validate_plan({"tempo": 90, "length_bars": 2, "chords": ["C", "G7"]})
    assert plan["voicing"] == DEFAULT_TASTE_LIKE["voicing"]
    assert plan["register"] == DEFAULT_TASTE_LIKE["register"]
    assert plan["velocity_range"] == DEFAULT_TASTE_LIKE["velocity_range"]
    assert plan["voicing_defaulted"] is True
    assert plan["register_defaulted"] is True
    assert plan["velocity_range_defaulted"] is True


DEFAULT_TASTE_LIKE = {"voicing": "closed", "register": "mid", "velocity_range": [64, 96]}


def test_rejects_out_of_range_and_unknowns():
    with pytest.raises(MusicPlanError):
        validate_plan({"tempo": 39, "length_bars": 1, "chords": ["C"]})
    with pytest.raises(MusicPlanError):
        validate_plan({"tempo": 221, "length_bars": 1, "chords": ["C"]})
    with pytest.raises(MusicPlanError):
        validate_plan({"tempo": 88, "length_bars": 0, "chords": []})
    with pytest.raises(MusicPlanError):
        validate_plan({"tempo": 88, "length_bars": 33, "chords": ["C"] * 33})
    with pytest.raises(MusicPlanError):
        validate_plan({"tempo": 88, "length_bars": 2, "chords": ["C", "Hmaj7"]})
    with pytest.raises(MusicPlanError):
        validate_plan({"tempo": 88, "length_bars": 2, "chords": ["C", "Dbsus24"]})
    with pytest.raises(MusicPlanError):
        validate_plan({"tempo": 88, "length_bars": 1, "chords": ["C"], "meter": "7/8"})
    with pytest.raises(MusicPlanError):
        validate_plan({"tempo": 88, "length_bars": 1, "chords": ["C"], "voicing": "spicy"})
    with pytest.raises(MusicPlanError):
        validate_plan({"tempo": 88, "length_bars": 1, "chords": ["C"], "register": "subsonic"})
    with pytest.raises(MusicPlanError):
        validate_plan({"tempo": 88, "length_bars": 1, "chords": ["C"], "velocity_range": [200, 300]})
    with pytest.raises(MusicPlanError):
        validate_plan({"tempo": 88, "length_bars": 1, "chords": ["C"], "velocity_range": [90, 20]})
    with pytest.raises(MusicPlanError):
        validate_plan("not a dict")
    # chords must fill the bars exactly
    with pytest.raises(MusicPlanError, match="must fill"):
        validate_plan({"tempo": 88, "length_bars": 4, "chords": ["C", "G"]})
    # velocity bounds inclusive edges are legal
    assert validate_plan({"tempo": 88, "length_bars": 1, "chords": ["C"], "velocity_range": [1, 127]})


def test_chord_count_matches_bars_when_bars_valid():
    plan = validate_plan({"tempo": 88, "length_bars": 2, "chords": ["C", "Am"]})
    assert plan["chords"] == ["C", "Am"]


def test_parse_chord_canonical():
    assert parse_chord("Bbmaj7") == (10, "maj7")
    assert parse_chord("C") == (0, "maj")
    assert parse_chord("Dm9") == (2, "m9")
    assert parse_chord("A7sus4") == (9, "7sus4")
    assert parse_chord("ebm7b5") == (3, "m7b5")
    assert chord_notes("Cmaj7") == (0, 4, 7, 11)
    with pytest.raises(MusicPlanError):
        parse_chord("Xmaj7")
    with pytest.raises(MusicPlanError):
        parse_chord("Cflat9")


def test_json_round_trip():
    text = json.dumps(SHOEGAZE_PLAN)
    plan = plan_from_json(text)
    assert plan["tempo"] == 88
    with pytest.raises(MusicPlanError):
        plan_from_json("{not json")


# --- compiler: determinism is the contract -----------------------------------

def test_same_plan_same_bytes():
    plan = validate_plan(SHOEGAZE_PLAN)
    a = compile_plan(plan)
    b = compile_plan(validate_plan(dict(SHOEGAZE_PLAN)))
    assert a["smf"] == b["smf"]
    assert a["phrase_hash"] == b["phrase_hash"]
    assert a["event_count"] == b["event_count"]
    # and a hash differs when anything musical changes
    tweaked = validate_plan({**SHOEGAZE_PLAN, "velocity_range": [48, 77]})
    assert phrase_hash(compile_events(tweaked)) != a["phrase_hash"]


def test_wide_voicing_deterministic_notes():
    plan = validate_plan(SHOEGAZE_PLAN)
    compiled = compile_events(plan)
    dmin9 = compiled["bars"][0]
    # Dm9 mid root: D3=50 stack (0,3,7,10,14) -> [50,53,57,60,64]; wide drops
    # voice 3 an octave: 57-12=45
    notes = [entry["note"] for entry in dmin9["notes"]]
    assert notes == [45, 50, 53, 60, 64]
    # velocities descend from the top of the range on the lowest note (root)
    velocities = [entry["velocity"] for entry in dmin9["notes"]]
    assert velocities == sorted(velocities, reverse=True)
    lo, hi = plan["velocity_range"]
    assert lo <= min(velocities) and max(velocities) <= hi


def test_shell_voicing_two_notes():
    plan = validate_plan({"tempo": 90, "length_bars": 1, "chords": ["Cmaj7"], "voicing": "shell"})
    compiled = compile_events(plan)
    notes = [e["note"] for e in compiled["bars"][0]["notes"]]
    # C3 root + highest extension B4? No: stack is C4 E4 G4 B4 -> root + B
    assert notes[0] == 12 * 4 + 0  # C4 (mid register)
    assert len(notes) == 2
    assert notes[1] > notes[0]


def test_register_moves_the_root():
    base = {"tempo": 90, "length_bars": 1, "chords": ["C"]}
    low = compile_events(validate_plan({**base, "register": "low"}))
    mid = compile_events(validate_plan(base))
    high = compile_events(validate_plan({**base, "register": "high"}))
    assert [e["note"] for e in low["bars"][0]["notes"]][0] == 12 * 3 + 0  # root_oct 2 -> C2=36
    assert [e["note"] for e in mid["bars"][0]["notes"]][0] == 12 * 4 + 0  # root_oct 3 -> C3=48
    assert [e["note"] for e in high["bars"][0]["notes"]][0] == 12 * 5 + 0  # root_oct 4 -> C4=60


def test_compiler_refuses_unvalidated_plan():
    bad = dict(SHOEGAZE_PLAN)
    bad["voicing"] = "spicy"
    with pytest.raises(MusicPlanError, match="refuses unvalidated"):
        compile_events(bad)


def test_timing_and_event_count():
    plan = validate_plan(SHOEGAZE_PLAN)
    compiled = compile_events(plan)
    assert compiled["ticks_per_bar"] == 1920
    # 8 bars: Dm9(5) Bbmaj7(4) Fadd9(4) C(3) Dm9(5) Bbmaj7(4) Gm9(5) A7sus4(4)
    # = 34 notes -> 68 on+off events (C is a triad, maj7/7sus4/add9 are 4-note)
    assert compiled["event_count"] == 68
    bar4 = compiled["bars"][3]  # C major triad
    assert bar4["start_tick"] == 3 * 1920 and bar4["end_tick"] == 4 * 1920
    # mid register root octave = 3 -> C3 = 48; wide voicing keeps triads stacked
    assert [e["note"] for e in bar4["notes"]] == [48, 52, 55]


# --- SMF structure ------------------------------------------------------------

def test_smf_is_structurally_real_and_deterministic():
    plan = validate_plan(SHOEGAZE_PLAN)
    compiled = compile_plan(plan)
    smf = compiled["smf"]
    assert smf[:4] == b"MThd"
    assert smf[4:8] == (6).to_bytes(4, "big")
    assert b"MTrk" in smf
    # tempo meta: 88 BPM -> 60_000_000/88 = 681818 us
    assert bytes.fromhex("ff5103") in smf
    assert (60_000_000 // 88).to_bytes(3, "big") in smf
    assert smf.endswith(b"\xff\x2f\x00")
    # determinism: events_to_smf twice on same structure is byte-identical
    assert events_to_smf(compiled) == smf


def test_write_smf_writes_bytes(tmp_path: Path):
    compiled = compile_plan(validate_plan(SHOEGAZE_PLAN))
    out = write_smf(compiled, str(tmp_path / "phrase" / "mid"))
    assert Path(out).read_bytes() == compiled["smf"]


def test_varlen_boundaries():
    assert _varlen(0) == b"\x00"
    assert _varlen(127) == b"\x7f"
    assert _varlen(128) == b"\x81\x00"
    assert _varlen(1920) == b"\x8f\x00"
    with pytest.raises(MusicPlanError):
        _varlen(-1)