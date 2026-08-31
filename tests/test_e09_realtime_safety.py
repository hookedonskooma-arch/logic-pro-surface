"""E09: render path must not allocate, lock, or do I/O. Static scan tonight."""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AU_ROOT = REPO / "audio-unit"

RENDER_FILES = [
    AU_ROOT / "cpp-dsp" / "PhraseKernel.cpp",
    AU_ROOT / "cpp-dsp" / "PhraseKernel.h",
    AU_ROOT / "objcxx" / "KernelAdapter.mm",
]

FORBIDDEN = re.compile(
    r"\b("
    r"malloc|calloc|realloc|free|new|delete|"
    r"std::mutex|std::lock_guard|std::unique_lock|std::scoped_lock|"
    r"pthread_mutex|os_unfair_lock|NSLock|"
    r"fopen|fclose|fread|fwrite|ifstream|ofstream|"
    r"std::cout|std::cerr|printf|"
    r"sleep|std::this_thread"
    r")\b"
)

BEGIN = "// RENDER_PATH_BEGIN"
END = "// RENDER_PATH_END"


def _regions(text: str) -> list[str]:
    regions = []
    start = 0
    while True:
        i = text.find(BEGIN, start)
        if i < 0:
            break
        j = text.find(END, i)
        assert j > i, "RENDER_PATH_BEGIN without END"
        regions.append(text[i:j])
        start = j + len(END)
    return regions


def test_render_markers_exist():
    cpp = (AU_ROOT / "cpp-dsp" / "PhraseKernel.cpp").read_text()
    mm = (AU_ROOT / "objcxx" / "KernelAdapter.mm").read_text()
    assert BEGIN in cpp and END in cpp
    assert BEGIN in mm and END in mm
    assert "malloc" not in cpp
    assert "new " not in cpp


def test_render_regions_have_no_alloc_io_or_locks():
    failures = []
    for path in RENDER_FILES:
        text = path.read_text()
        regions = _regions(text)
        assert regions, f"{path.name} has no RENDER_PATH region"
        for chunk in regions:
            for lineno, line in enumerate(chunk.splitlines(), 1):
                stripped = line.split("//", 1)[0]
                if FORBIDDEN.search(stripped):
                    failures.append(f"{path.name} render:{lineno}: {line.strip()}")
    assert failures == [], "E09 fail-closed:\n" + "\n".join(failures)


def test_swift_does_not_implement_the_render_loop():
    swift = (AU_ROOT / "swift" / "MidiFxAudioUnit.swift").read_text()
    assert "internalRenderBlock" in swift
    assert "adapter.internalRenderBlock()" in swift
    assert "malloc" not in swift
    # Swift file must not contain its own DSP loop.
    assert "triggerPhrase" in swift
    assert "for " not in swift.split("internalRenderBlock", 1)[1]
