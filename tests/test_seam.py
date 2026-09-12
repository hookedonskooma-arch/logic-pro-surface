"""The composition seam: honest envelopes, offline contract, no fake sends.

Pins the machine boundary of composition v0.1:
- forced-offline / missing mido / loopback capture -> uncertain, nothing sent
- send without independent capture -> uncertain (adapter success only)
- captured hash mismatch -> failed
- captured hash match -> confirmed, human-receipt note intact (hash contract
  pinned without mido: same inverse tempo math on both sides)
- play CLI refuses to send without --go (tier 1); plan never sends
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gnomo.cli import main as cli_main
from gnomo.midi_compiler import compile_plan
from gnomo.music_plan import validate_plan
from gnomo.seam import _phrase_hash_of_captured, play_plan, play_plan_with_ports

SHOEGAZE_PLAN = {
    "tempo": 88,
    "key": "D minor",
    "length_bars": 8,
    "chords": ["Dm9", "Bbmaj7", "Fadd9", "C", "Dm9", "Bbmaj7", "Gm9", "A7sus4"],
    "voicing": "wide",
    "register": "mid",
    "velocity_range": [48, 76],
}

OUT = "IAC Driver Fake Out"


def _compiled():
    return compile_plan(validate_plan(SHOEGAZE_PLAN))


# --- offline / environment contract ------------------------------------------

def test_forced_offline_is_uncertain_and_sends_nothing():
    env = play_plan(_compiled(), out_port=OUT, force_offline=True)
    assert env["status"] == "uncertain"
    assert env["adapter_result"]["success"] is False
    assert env["readback"] is None
    assert "skip is not pass" in " ".join(env["notes"])


def test_missing_mido_is_uncertain(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def blocked(name, *a, **k):
        if name == "mido":
            raise ImportError("mido not installed")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", blocked)
    env = play_plan(_compiled(), out_port=OUT, force_offline=False)
    assert env["status"] == "uncertain"
    assert env["adapter_result"]["reason"] == "mido_not_installed"


def test_loopback_capture_refused_as_pass_bit():
    env = play_plan(_compiled(), out_port=OUT, capture_port=OUT, force_offline=False)
    # loopback refused before any port work; mido presence irrelevant here
    assert env["status"] == "uncertain"
    assert env["adapter_result"]["reason"] == "capture_port_equals_send_port_loopback_refused"
    assert env["readback"] is None


# --- CLI: plan (tier 0) and play (tier 1 --go gate) ---------------------------

@pytest.fixture
def plan_file(tmp_path: Path) -> str:
    p = tmp_path / "plan.json"
    p.write_text(json.dumps(SHOEGAZE_PLAN), encoding="utf-8")
    return str(p)


def test_cli_plan_compiles_and_never_sends(plan_file, tmp_path, capsys):
    out = str(tmp_path / "phrase.mid")
    rc = cli_main(["--quiet", "--json", "plan", "--file", plan_file, "--out", out])
    assert rc == 0
    record = json.loads(capsys.readouterr().out)
    assert record["accepted"] is True
    assert record["tier"] == 0
    assert record["phrase_hash"] == _compiled()["phrase_hash"]
    assert Path(out).exists()
    # a plan never reaches a port: no send envelope in the record
    assert "envelope" not in record


def test_cli_plan_rejects_bad_plan(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"tempo": 88, "length_bars": 1, "chords": ["H9"]}), encoding="utf-8")
    rc = cli_main(["--quiet", "--json", "plan", "--file", str(bad)])
    assert rc == 0  # a rejection is itself a printed decision
    record = json.loads(capsys.readouterr().out)
    assert record["accepted"] is False
    assert "unrecognized chord" in record["error"]


def test_cli_play_without_go_refuses_to_send(plan_file, capsys):
    rc = cli_main(["--quiet", "--json", "play", "--file", plan_file, "--out", OUT])
    assert rc == 0
    record = json.loads(capsys.readouterr().out)
    assert record["tier"] == 1
    assert record["authority"] == "propose"
    assert record["mode"] == "with"
    assert record["blockers"] == ["no --go on the play command"]


def test_cli_play_offline_with_go_is_uncertain(plan_file, capsys):
    rc = cli_main(
        ["--quiet", "--json", "play", "--file", plan_file, "--out", OUT, "--go", "--offline"]
    )
    assert rc == 0
    record = json.loads(capsys.readouterr().out)
    env = record["envelope"]
    assert env["status"] == "uncertain"
    assert env["adapter_result"]["success"] is False
    # ledger got a row: a play attempt is a decision, even offline
    assert record["ledger"]["written"] is True


def test_cli_play_bad_plan_reports_rejection(capsys):
    rc = cli_main(
        ["--quiet", "--json", "play", "--json-text", '{"tempo": 5000}', "--out", OUT, "--go"]
    )
    assert rc == 0
    record = json.loads(capsys.readouterr().out)
    assert record["accepted"] is False
    assert "tempo" in record["error"]


# --- port-free execution core (inject I/O) ------------------------------------

def test_play_plan_with_ports_round_trip():
    compiled = _compiled()
    sent: list[bytes] = []
    captured: list = []

    class FakeMsg:
        def __init__(self, raw: bytes):
            self.raw = raw
            self.type = "note_on" if raw[0] == 0x90 else "note_off"
            self.note = raw[1]
            self.velocity = raw[2]

    def send(raw: bytes) -> None:
        sent.append(raw)
        captured.append(FakeMsg(raw))

    result = play_plan_with_ports(compiled, send=send, receive_pending=lambda: captured)
    assert result["events_sent"] == compiled["event_count"]
    assert len(captured) == result["events_sent"]


# --- the capture hash contract (no mido needed) -------------------------------

class _Msg:
    def __init__(self, kind: str, note: int, velocity: int, time: float):
        self.type = kind
        self.note = note
        self.velocity = velocity
        self.time = time


def test_capture_hash_matches_compiled_when_notes_echo_true():
    """Echoed notes with true-ish times reconstruct the exact compiled hash.

    This pins the unit conversion: captured seconds -> ticks via tempo math,
    the inverse of _schedule_events. If this ever drifts, the seam would
    call a good capture `failed` or a bad one `confirmed`.
    """
    compiled = _compiled()
    spq = 60.0 / compiled["tempo"]  # seconds per quarter note
    msgs = []
    for bar in compiled["bars"]:
        for entry in bar["notes"]:
            t_on = (bar["start_tick"] / compiled["ppq"]) * spq
            msgs.append(_Msg("note_on", entry["note"], entry["velocity"], t_on))
            t_off = (bar["end_tick"] / compiled["ppq"]) * spq
            msgs.append(_Msg("note_off", entry["note"], 0, t_off))
    h = _phrase_hash_of_captured(msgs, compiled["ppq"], compiled["tempo"])
    assert h == compiled["phrase_hash"]


def test_capture_hash_is_none_without_complete_pairs():
    compiled = _compiled()
    msgs = [_Msg("note_on", 60, 90, 0.0)]  # an orphan note_on: no pair
    assert _phrase_hash_of_captured(msgs, compiled["ppq"], compiled["tempo"]) is None


def test_capture_hash_changes_when_velocity_changes():
    compiled = _compiled()
    spq = 60.0 / compiled["tempo"]
    msgs = []
    for bar in compiled["bars"]:
        for entry in bar["notes"]:
            t_on = (bar["start_tick"] / compiled["ppq"]) * spq
            vel = entry["velocity"] - 5  # tampered
            msgs.append(_Msg("note_on", entry["note"], vel, t_on))
            t_off = (bar["end_tick"] / compiled["ppq"]) * spq
            msgs.append(_Msg("note_off", entry["note"], 0, t_off))
    h = _phrase_hash_of_captured(msgs, compiled["ppq"], compiled["tempo"])
    assert h != compiled["phrase_hash"]