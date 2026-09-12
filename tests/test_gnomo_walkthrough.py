"""Guided setup: a step the gnome cannot verify is never a step it passes.

The walkthrough exists because GNOMO cannot click Logic's Control Surfaces
window. These tests pin the honesty of that boundary: unknown stays unknown,
a broken check fails closed, and only an MCU echo closes step 5.
"""

from __future__ import annotations

import json

import pytest

from gnomo import ledger, mouth, walkthrough
from gnomo.cli import main as gnomo_main


def test_no_step_claims_done_without_a_mac():
    """On this Linux host nothing is set up, so nothing may report done."""
    for row in walkthrough.evaluate():
        assert row["state"] in (walkthrough.TODO, walkthrough.UNKNOWN), row


def test_every_step_carries_an_instruction():
    for step in walkthrough.STEPS:
        assert step.detail, step.step_id
        assert step.spoken, step.step_id


def test_broken_check_fails_closed_to_unknown(monkeypatch):
    def boom():
        raise RuntimeError("coremidi exploded")

    monkeypatch.setattr(walkthrough.STEPS[0], "check", boom)
    row = walkthrough.evaluate()[0]
    assert row["state"] == walkthrough.UNKNOWN
    assert "check_failed" in row["evidence"]


def test_missing_dependency_is_unknown_not_done(monkeypatch):
    def no_mido():
        raise ImportError("no module named mido")

    monkeypatch.setattr(walkthrough.STEPS[0], "check", no_mido)
    assert walkthrough.evaluate()[0]["state"] == walkthrough.UNKNOWN


@pytest.mark.parametrize(
    "status,method,expected",
    [
        ("confirmed", "mcu_feedback", walkthrough.DONE),
        ("confirmed", "ax_live", walkthrough.TODO),
        ("confirmed", None, walkthrough.TODO),
        ("uncertain", "mcu_feedback", walkthrough.TODO),
        ("failed", "mcu_feedback", walkthrough.TODO),
    ],
)
def test_echo_step_closes_only_on_mcu_feedback(monkeypatch, status, method, expected):
    """AX receipts and adapter sends do not finish setup. Only the echo does."""
    from logic_probe import channels

    monkeypatch.setattr(
        channels,
        "mixer_set_volume",
        lambda *_a, **_k: {"status": status, "readback": {"method": method}},
    )
    assert walkthrough._check_echo()["state"] == expected


def test_current_returns_first_unfinished_step():
    rows = [
        {"step": "a", "state": walkthrough.DONE},
        {"step": "b", "state": walkthrough.UNKNOWN},
        {"step": "c", "state": walkthrough.TODO},
    ]
    assert walkthrough.current(rows)["step"] == "b"


def test_current_is_none_only_when_all_done():
    rows = [{"step": "a", "state": walkthrough.DONE}, {"step": "b", "state": walkthrough.DONE}]
    assert walkthrough.current(rows) is None


def test_unknown_never_counts_as_finished():
    rows = [{"step": "a", "state": walkthrough.UNKNOWN}]
    assert walkthrough.current(rows) is not None


def test_ports_step_warns_about_the_swap():
    """Swapped In/Out is the silent mcu_no_echo trap. It must be called out."""
    ports = next(s for s in walkthrough.STEPS if s.step_id == "ports")
    assert ports.trap and "mcu_no_echo" in ports.trap


def test_install_step_warns_off_rebuild_defaults():
    install = next(s for s in walkthrough.STEPS if s.step_id == "install")
    assert install.trap and "Rebuild Defaults" in install.trap


def test_cli_setup_names_one_step(capsys, monkeypatch, tmp_path):
    monkeypatch.setenv(mouth.MUTE_ENV, "1")
    monkeypatch.setattr(ledger, "LEDGER_PATH", tmp_path / "decisions.jsonl")
    assert gnomo_main(["--json", "setup", "mcu"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["current_step"] == "iac"
    assert len(payload["steps"]) == len(walkthrough.STEPS)
    assert payload["tier"] == 0, "checking setup is read-only; it acts for you"


def test_failed_fix_still_gives_a_next_step(capsys, monkeypatch, tmp_path):
    """"Error, no next action" is the one outcome setup must never produce."""
    from logic_probe import midi_io

    monkeypatch.setenv(mouth.MUTE_ENV, "1")
    monkeypatch.setattr(ledger, "LEDGER_PATH", tmp_path / "decisions.jsonl")
    monkeypatch.setattr(
        midi_io,
        "ensure_iac_mcu_buses",
        lambda: {"attempted": True, "error": "coremidi_unavailable:nope"},
    )
    assert gnomo_main(["setup", "mcu", "--fix"]) == 0
    out = capsys.readouterr().out
    assert "coremidi_unavailable" in out, "must say what broke"
    assert "step 1 of 5" in out, "must still name the step"
    assert "Audio MIDI Setup" in out, "must offer the by-hand path"


def test_fix_failure_does_not_mark_the_step_done(monkeypatch, tmp_path):
    from logic_probe import midi_io

    monkeypatch.setenv(mouth.MUTE_ENV, "1")
    monkeypatch.setattr(ledger, "LEDGER_PATH", tmp_path / "decisions.jsonl")
    monkeypatch.setattr(
        midi_io, "ensure_iac_mcu_buses", lambda: {"attempted": True, "error": "boom"}
    )
    assert walkthrough.current() is not None


def test_first_step_carries_a_by_hand_path():
    iac = next(s for s in walkthrough.STEPS if s.step_id == "iac")
    assert iac.manual, "the one auto step needs a manual fallback"
    assert any("logic-probe-mcu-cmd" in line for line in iac.manual)
