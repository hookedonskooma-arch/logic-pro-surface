"""E04: Scripter is not a project API. Attempt to rename/create track must fail."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPTER = REPO / "scripter"

# Apple-documented Scripter JS MIDI plug-in surface (not a project API).
SCRIPTER_API = {
    "HandleMIDI",
    "ProcessMIDI",
    "PluginParameters",
    "GetParameter",
    "SetParameter",
    "UpdatePluginParameters",
    "ParameterChanged",
    "Reset",
    "Idle",
    "Trace",
    "NeedsTimingInfo",
    "GetTimingInfo",
    "MIDI",
    "Note",
    "NoteOn",
    "NoteOff",
    "ControlChange",
    "ProgramChange",
    "PitchBend",
    "ChannelPressure",
    "PolyPressure",
    "TargetEvent",
}

FORBIDDEN_PROJECT_API = {
    "RenameProject",
    "CreateTrack",
    "NewTrack",
    "SetProjectName",
    "DeleteTrack",
    "SaveProject",
    "OpenProject",
}


class ScripterNotProjectAPI(LookupError):
    pass


class ScripterHost:
    """Linux-safe stand-in: only documented Scripter MIDI APIs exist."""

    def call(self, name: str, *args):
        if name in FORBIDDEN_PROJECT_API or name not in SCRIPTER_API:
            raise ScripterNotProjectAPI(name)
        return None


def test_scripter_is_javascript_fixture():
    src = (SCRIPTER / "e03_transpose_plus12.js").read_text()
    assert "function HandleMIDI" in src
    assert "event.pitch += 12" in src
    assert "not Lua" in src


def test_e04_fixture_expects_missing_project_api():
    src = (SCRIPTER / "e04_not_project_api.js").read_text()
    assert "RenameProject" in src
    assert "CreateTrack" in src
    assert "not a Logic project API" in src or "not a project API" in src.lower() or "not a Logic project API" in src


def test_host_rejects_rename_and_create_track():
    host = ScripterHost()
    host.call("HandleMIDI")
    host.call("ProcessMIDI")
    with pytest.raises(ScripterNotProjectAPI):
        host.call("RenameProject", "x")
    with pytest.raises(ScripterNotProjectAPI):
        host.call("CreateTrack")
    with pytest.raises(ScripterNotProjectAPI):
        host.call("NewTrack")


def test_forbidden_names_are_not_in_scripter_api():
    overlap = SCRIPTER_API & FORBIDDEN_PROJECT_API
    assert overlap == set()
