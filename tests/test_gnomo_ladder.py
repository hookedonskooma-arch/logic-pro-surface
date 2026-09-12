"""GNOMO decision ladder: authority is earned, never assumed.

These tests guard the property that makes the companion usable: it cannot
talk itself into acting. Unknown is not a yes, and a rung with no rollback
is not a rung.
"""

from __future__ import annotations

import json

import pytest

from gnomo import ledger, mouth, persona, state
from gnomo.cli import main as gnomo_main
from gnomo.ladder import (
    RULES,
    TIER_ACT,
    TIER_ASK,
    TIER_PROPOSE,
    TIER_REFUSE,
    classify,
    decide,
)


# --- fail closed ---------------------------------------------------------


@pytest.mark.parametrize(
    "action",
    [
        "frobnicate the widget",
        "do the thing we talked about",
        "handle the vocals",
        "",
    ],
)
def test_unmatched_action_never_acts(action):
    """An action the ladder does not recognise is handed back, not run."""
    if not action:
        with pytest.raises(ValueError):
            decide(action)
        return
    assert decide(action)["tier"] == TIER_ASK


def test_default_is_ask_not_act():
    d = decide("something entirely novel and unlisted")
    assert d["authority"] == "ask"
    assert d["mode"] == "you"
    assert d["tier"] != TIER_ACT


# --- never rungs ---------------------------------------------------------


@pytest.mark.parametrize(
    "action",
    [
        "how does the mix sound",
        "does the 808 sound better now",
        "give it a listen and tell me",
        "did you hear that",
    ],
)
def test_claiming_ears_is_refused(action):
    """This layer has no ears. No tier below 3 may pretend otherwise."""
    assert decide(action)["tier"] == TIER_REFUSE


@pytest.mark.parametrize(
    "action",
    [
        "rebuild defaults in control surfaces",
        "route MELEGI audio through the bus",
        "mark MCU echo as verified",
        "just assume the tempo is 92",
        "use the AX readback to confirm the region",
    ],
)
def test_protected_surfaces_are_refused(action):
    assert decide(action)["tier"] == TIER_REFUSE


def test_refusal_never_downgrades_by_wording():
    """A refusal phrased as a read is still a refusal: order is authority order."""
    assert decide("check how the guitar sounds")["tier"] == TIER_REFUSE


# --- rollback invariant --------------------------------------------------


def test_every_propose_rule_states_a_rollback():
    """Tier 1 is 'reversible'. A rung without an undo is a lie about the tier."""
    missing = [r.pattern.pattern for r in RULES if r.tier == TIER_PROPOSE and not r.rollback]
    assert not missing, missing


def test_propose_without_rollback_is_downgraded(monkeypatch):
    rule = classify("set the fader to -6 dB")
    assert rule is not None and rule.tier == TIER_PROPOSE
    monkeypatch.setattr(rule, "rollback", None)
    d = decide("set the fader to -6 dB")
    assert d["tier"] == TIER_ASK
    assert d["downgraded"]


def test_acts_are_reversible_and_touch_no_session():
    for action in ("read the envelope", "park this idea", "run the tests"):
        assert decide(action)["tier"] == TIER_ACT
        assert decide(action)["mode"] == "for"


# --- one voice, one action ----------------------------------------------


@pytest.mark.parametrize(
    "action",
    ["set track 3 to -6 dB", "master this to -9 LUFS", "park the intro idea", "did you hear that"],
)
def test_spoken_line_is_at_most_two_sentences(action):
    line = persona.line(decide(action))
    assert line.count(".") <= 3, line  # two sentences plus a decimal or abbreviation
    assert len(line) < 240, line


def test_spoken_line_never_claims_a_listen():
    for action in ("how does the mix sound", "give it a listen"):
        line = persona.line(decide(action)).lower()
        assert "sounds good" not in line
        assert line.startswith("no.")


def test_plain_keeps_underscored_filenames_readable():
    assert persona.plain("see `MCP_CAPABILITIES.md`") == "see MCP_CAPABILITIES.md"


# --- grounding: never invent state --------------------------------------


def test_snapshot_denies_ears_and_project_reads():
    snap = state.snapshot()
    assert snap["can_hear_audio"] is False
    assert snap["can_read_logic_project"] is False


def test_snapshot_is_grounded_in_real_files(repo_root):
    snap = state.snapshot()
    for rel in snap["grounded_in"]:
        assert (repo_root / rel).is_file(), rel


def test_missing_studio_notes_yield_nothing_not_fiction(monkeypatch, tmp_path):
    monkeypatch.setattr(state, "PROJECT_STATE", tmp_path / "gone.md")
    monkeypatch.setattr(state, "CURRENT_TASKS", tmp_path / "also-gone.md")
    snap = state.snapshot()
    assert snap["now"] is None
    assert snap["blockers"] == []
    assert snap["unknown"], "a gnome with no notes must say so"


# --- mouth: honest degradation ------------------------------------------


def test_mute_is_reported_not_faked(monkeypatch):
    monkeypatch.setenv(mouth.MUTE_ENV, "1")
    said = mouth.speak("MCU echo is the pass bit")
    assert said["spoke"] is False
    assert mouth.MUTE_ENV in said["reason"]


def test_no_say_binary_means_not_spoken(monkeypatch):
    """The say-presence check lives in voz now; that is the single mouth."""
    from voz import mouth as voz_mouth

    monkeypatch.delenv(mouth.MUTE_ENV, raising=False)
    monkeypatch.setattr(voz_mouth.shutil, "which", lambda _name: None)
    ok, why = mouth.available()
    assert ok is False
    assert "macOS" in why
    assert mouth.speak("anything")["spoke"] is False


# --- ledger --------------------------------------------------------------


def test_ledger_roundtrip(tmp_path):
    path = tmp_path / "decisions.jsonl"
    written, where = ledger.append({"action": "a", "mode": "for"}, path=path)
    assert written and where == str(path)
    ledger.append({"action": "b", "mode": "you"}, path=path)
    rows = ledger.read(10, path=path)
    assert [r["action"] for r in rows] == ["a", "b"]


def test_ledger_write_failure_is_reported(tmp_path):
    blocked = tmp_path / "file.txt"
    blocked.write_text("not a directory")
    written, why = ledger.append({"action": "a"}, path=blocked / "nested.jsonl")
    assert written is False
    assert "failed" in why


# --- CLI -----------------------------------------------------------------


def _run(capsys, argv):
    assert gnomo_main(argv) == 0
    return capsys.readouterr().out


def test_cli_decide_json_shape(capsys, monkeypatch, tmp_path):
    monkeypatch.setenv(mouth.MUTE_ENV, "1")
    monkeypatch.setattr(ledger, "LEDGER_PATH", tmp_path / "decisions.jsonl")
    payload = json.loads(_run(capsys, ["--json", "decide", "play the transport"]))
    for key in ("companion", "timestamp", "tier", "authority", "mode", "spoken", "voice"):
        assert key in payload, key
    assert payload["companion"] == "GNOMO"
    assert payload["voice"]["spoke"] is False


def test_cli_next_names_one_thing(capsys, monkeypatch, tmp_path):
    monkeypatch.setenv(mouth.MUTE_ENV, "1")
    monkeypatch.setattr(ledger, "LEDGER_PATH", tmp_path / "decisions.jsonl")
    out = _run(capsys, ["next"])
    assert "GNOMO" in out
    assert "One thing:" in out or "one thing" in out.lower()


def test_cli_park_writes_and_stamps(capsys, monkeypatch, tmp_path):
    monkeypatch.setenv(mouth.MUTE_ENV, "1")
    monkeypatch.setattr(state, "PARKING_LOT", tmp_path / "PARKING_LOT.md")
    monkeypatch.setattr(state, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(ledger, "LEDGER_PATH", tmp_path / "decisions.jsonl")
    payload = json.loads(_run(capsys, ["--json", "park", "chop the intro tighter"]))
    assert payload["parked"] is True
    assert payload["timestamp"]
    assert "chop the intro tighter" in (tmp_path / "PARKING_LOT.md").read_text()


def test_cli_empty_ask_exits_nonzero_without_traceback(capsys, monkeypatch):
    monkeypatch.setenv(mouth.MUTE_ENV, "1")
    assert gnomo_main(["decide", "   "]) == 2
    assert "GNOMO:" in capsys.readouterr().err


# --- the hearing line ----------------------------------------------------
#
# Every allow case ships next to its refusing twin. A regex widened later
# breaks a test here instead of quietly breaking the promise.

HEARING_PAIRS = [
    ("take a voice note", "transcribe the guitar take"),
    ("transcribe what I just said", "transcribe the mix"),
    ("what did I just say", "what did that take sound like"),
    ("voice memo this idea", "dictate a note about the snare"),
    ("note this down", "transcribe the vocal take"),
]


@pytest.mark.parametrize("allowed,refused", HEARING_PAIRS)
def test_hearing_the_human_is_allowed(allowed, refused):
    """Transcribing Chris is text out. It is not metering audio."""
    assert decide(allowed)["tier"] == TIER_ACT, allowed


@pytest.mark.parametrize("allowed,refused", HEARING_PAIRS)
def test_hearing_the_mix_stays_refused(allowed, refused):
    """Name a musical object and it is audio analysis, whatever the verb."""
    assert decide(refused)["tier"] == TIER_REFUSE, refused


def test_transcription_never_reaches_a_judgement():
    """Text out, never an opinion. 'Sounds good' is refused however asked."""
    for action in (
        "transcribe this and tell me if it sounds good",
        "listen and say whether the take is better",
    ):
        assert decide(action)["tier"] == TIER_REFUSE, action


def test_the_verb_take_is_not_a_musical_take():
    """'take a voice note' must not trip on the noun 'take'."""
    assert decide("take a voice note")["tier"] == TIER_ACT
    assert decide("transcribe that take")["tier"] == TIER_REFUSE


def test_bare_hearing_words_are_still_refused():
    """Widening for transcription must not reopen the old hole."""
    for action in ("give it a listen", "how does the guitar sound", "did you hear that"):
        assert decide(action)["tier"] == TIER_REFUSE, action


def test_allow_rung_sits_above_its_refusing_twin():
    """Order is load-bearing: the narrow allow is checked before the refusal."""
    tiers = [r.tier for r in RULES[:2]]
    assert tiers == [TIER_ACT, TIER_REFUSE], tiers
