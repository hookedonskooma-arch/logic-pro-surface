"""MELEGI extract is AU MIDI FX only. Not TTS, not Ollama, not VST."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MELEGI = REPO / "audio-unit" / "melegi"


def test_extract_sources_exist():
    for rel in (
        "CMakeLists.txt",
        "Source/PluginProcessor.cpp",
        "Source/PluginProcessor.h",
        "Source/PluginEditor.cpp",
        "Source/PluginEditor.h",
        "Source/VozBridgeClient.h",
        "Resources/plugin_ui.html",
    ):
        assert (MELEGI / rel).is_file(), rel


def test_cmake_is_au_midi_fx_not_synth_not_vst():
    cmake = (MELEGI / "CMakeLists.txt").read_text()
    assert "FORMATS AU" in cmake
    assert "IS_MIDI_EFFECT TRUE" in cmake
    assert "IS_SYNTH FALSE" in cmake
    assert "NEEDS_MIDI_INPUT TRUE" in cmake
    assert "NEEDS_MIDI_OUTPUT TRUE" in cmake
    assert "Never VST" in cmake
    assert "never VST3" in cmake.lower() or "Never VST3" in cmake
    # Product format must not list VST.
    for line in cmake.splitlines():
        stripped = line.split("#", 1)[0]
        if "FORMATS" in stripped:
            assert "VST" not in stripped


def test_processor_is_midi_fx_without_audio_buses():
    cpp = (MELEGI / "Source" / "PluginProcessor.cpp").read_text()
    hdr = (MELEGI / "Source" / "PluginProcessor.h").read_text()
    assert "BusesProperties()" in cpp
    assert "isMidiEffect() const override" in hdr
    assert "return true" in hdr
    assert "IS_MIDI_EFFECT" not in cpp  # flag lives in CMake
    # No stereo in/out buses added in this extract.
    assert "withInput" not in cpp
    assert "withOutput" not in cpp


def test_ui_does_not_call_private_backend_or_ollama():
    html = (MELEGI / "Resources" / "plugin_ui.html").read_text()
    assert "127.0.0.1:4780" not in html
    assert "ws://127.0.0.1" not in html
    lowered = html.lower()
    # Allow the words in a "not Ollama" disclaimer; forbid a client.
    assert "ollama.com" not in lowered
    assert "/api/generate" not in lowered
    assert "vibe-producer" not in lowered
    assert "queuePhrase" in html
    assert "60" in html and "64" in html and "67" in html and "72" in html


def test_not_tts_not_passthrough_in_cmake_banner():
    cmake = (MELEGI / "CMakeLists.txt").read_text()
    assert "Not TTS" in cmake or "not TTS" in cmake
    assert "Not Ollama" in cmake or "not Ollama" in cmake
    assert "Not audio pass-through" in cmake or "not audio pass-through" in cmake
