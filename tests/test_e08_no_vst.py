"""E08: AU brick has FORMATS AU only. No VST / VST3 product path."""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AU_ROOT = REPO / "audio-unit"

SOURCE_GLOBS = (
    "*.txt",
    "*.cmake",
    "*.in",
    "*.h",
    "*.hpp",
    "*.c",
    "*.cpp",
    "*.mm",
    "*.m",
    "*.swift",
    "*.plist",
)

# Positive VST product-format declarations. Negation comments are allowed.
FORMATS_WITH_VST = re.compile(
    r"^\s*(?:set\s*\()?FORMATS\s+[^\n#]*\bVST",
    re.IGNORECASE | re.MULTILINE,
)
JUCE_BUILD_VST = re.compile(r"JucePlugin_Build_VST(?:3)?\s*[=,]?\s*1")
INCLUDE_VST = re.compile(r"#include\s*[<\"][^\n]*vst", re.IGNORECASE)
VST3_WRAPPER = re.compile(r"\b(createVST3?|AudioPluginFormat\s+VST|wrapperType_VST)\b")
NEGATION = re.compile(
    r"\b(not|never|no|without|isn't|is not|don't|do not|au only)\b",
    re.IGNORECASE,
)
VST_TOKEN = re.compile(r"\bVST3?\b", re.IGNORECASE)


def _source_files():
    files = []
    for pattern in SOURCE_GLOBS:
        files.extend(AU_ROOT.rglob(pattern))
    return [p for p in files if p.is_file()]


def test_cmake_formats_au_only():
    cmake = (AU_ROOT / "CMakeLists.txt").read_text()
    assert "Never VST" in cmake or "never VST" in cmake
    assert "FORMATS AU" in cmake or "AU only" in cmake or "AU MIDI Processor" in cmake
    assert FORMATS_WITH_VST.search(cmake) is None
    assert "VST3" not in cmake or NEGATION.search(
        next(line for line in cmake.splitlines() if "VST3" in line)
    )


def test_plist_is_aumi_midi_processor_not_synth():
    plist = (AU_ROOT / "Info.plist.in").read_text()
    assert "<string>aumi</string>" in plist
    assert "<string>aumu</string>" not in plist
    assert "<string>aumf</string>" not in plist


def test_no_vst_format_declarations_in_audio_unit():
    failures = []
    for path in _source_files():
        text = path.read_text(errors="replace")
        rel = path.relative_to(REPO)
        if FORMATS_WITH_VST.search(text):
            failures.append(f"{rel}: FORMATS includes VST")
        if JUCE_BUILD_VST.search(text):
            failures.append(f"{rel}: JucePlugin_Build_VST=1")
        if INCLUDE_VST.search(text):
            failures.append(f"{rel}: includes a VST header")
        if VST3_WRAPPER.search(text):
            failures.append(f"{rel}: VST wrapper symbol")
        for lineno, line in enumerate(text.splitlines(), 1):
            if not VST_TOKEN.search(line):
                continue
            if line.strip().startswith("#") or line.strip().startswith("//"):
                if NEGATION.search(line):
                    continue
            if NEGATION.search(line):
                continue
            failures.append(f"{rel}:{lineno}: VST string without negation: {line.strip()}")
    assert failures == [], "E08 fail-closed:\n" + "\n".join(failures)
