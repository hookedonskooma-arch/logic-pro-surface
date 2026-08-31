"""Envelope schema: confirmed | uncertain | failed. Never invent state."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from logic_probe.envelope import EnvelopeError, SEMANTIC_STATUSES, build_envelope, uncertain
from logic_probe.channels import ax_inspect_selected_track, mixer_set_volume, transport_play

REPO = Path(__file__).resolve().parents[1]
PROBE_ENV = {**dict(**__import__("os").environ), "PYTHONPATH": str(REPO / "logic-probe")}


REQUIRED_KEYS = ("before", "adapter_result", "readback", "verification", "status")


def test_status_vocabulary():
    assert SEMANTIC_STATUSES == frozenset({"confirmed", "uncertain", "failed"})


def test_confirmed_requires_readback_and_verification():
    with pytest.raises(EnvelopeError):
        build_envelope(
            probe_id="x",
            channel="mcu",
            operation="track.set_volume",
            requested={"track": 3, "db": -6.0},
            before={"db": None},
            adapter_result={"success": True},
            readback=None,
            verification={"passed": True},
            status="confirmed",
        )
    with pytest.raises(EnvelopeError):
        build_envelope(
            probe_id="x",
            channel="mcu",
            operation="track.set_volume",
            requested={"track": 3, "db": -6.0},
            before={"db": None},
            adapter_result={"success": True},
            readback={"method": "mcu_feedback", "observed_db": -6.0},
            verification={"passed": False, "reason": "mismatch"},
            status="confirmed",
        )


def test_ax_live_cannot_be_the_pass_bit():
    with pytest.raises(EnvelopeError):
        build_envelope(
            probe_id="x",
            channel="accessibility",
            operation="ax.inspect_selected_track",
            requested={},
            before=None,
            adapter_result={"success": True},
            readback={"method": "ax_live", "name": "Track 3"},
            verification={"passed": True},
            status="confirmed",
        )


def test_success_is_not_a_semantic_status():
    with pytest.raises(EnvelopeError):
        build_envelope(
            probe_id="x",
            channel="mcu",
            operation="transport.play",
            requested={},
            before=None,
            adapter_result={"success": True},
            readback=None,
            verification={"passed": False},
            status="success",
        )


def test_uncertain_helper_never_confirms():
    env = uncertain(
        probe_id="mixer_set_volume",
        channel="mcu",
        operation="track.set_volume",
        requested={"track": 3, "db": -6.0},
        reason="not_macos",
        before={"db": None, "source": None},
    )
    for key in REQUIRED_KEYS:
        assert key in env
    assert env["status"] == "uncertain"
    assert env["readback"] is None
    assert env["verification"]["passed"] is False
    assert env["before"]["db"] is None


def _keys_ok(env: dict):
    for key in REQUIRED_KEYS:
        assert key in env, key
    assert env["status"] in SEMANTIC_STATUSES
    assert env["status"] != "confirmed"


def test_v0_channels_are_uncertain():
    _keys_ok(mixer_set_volume(3, -6.0))
    _keys_ok(transport_play())
    ax = ax_inspect_selected_track()
    _keys_ok(ax)
    assert ax["channel"] == "accessibility"
    assert ax["status"] == "uncertain"


def _run_probe(*args: str) -> dict:
    cmd = [sys.executable, "-m", "logic_probe", *args]
    proc = subprocess.run(
        cmd,
        cwd=REPO,
        env=PROBE_ENV,
        capture_output=True,
        text=True,
        check=True,
    )
    env = json.loads(proc.stdout)
    _keys_ok(env)
    return env


def test_cli_mixer_set_volume_offline():
    env = _run_probe("mixer", "set-volume", "--track", "3", "--db", "-6")
    assert env["operation"] == "track.set_volume"
    assert env["requested"]["track"] == 3
    assert env["requested"]["db"] == -6.0
    assert env["status"] == "uncertain"
    assert env["before"] is not None
    assert env["readback"] is None


def test_cli_transport_play_offline():
    env = _run_probe("transport", "play")
    assert env["operation"] == "transport.play"
    assert env["status"] == "uncertain"


def test_cli_ax_inspect_never_confirmed():
    env = _run_probe("ax", "inspect-selected-track")
    assert env["status"] == "uncertain"
    assert env["status"] != "confirmed"
    assert "never fake confirmed" in " ".join(env.get("notes") or [])
