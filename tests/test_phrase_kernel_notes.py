"""Offline shape check: kernel source emits C3 E3 G3 C4. Not live E02.

No g++ required: we parse the C++ constants and run a bounded replica of
the preallocated queue. Live phrase hash against Logic remains UNKNOWN.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HDR = REPO / "audio-unit" / "cpp-dsp" / "PhraseKernel.h"
CPP = REPO / "audio-unit" / "cpp-dsp" / "PhraseKernel.cpp"


def _const(name: str) -> int:
    m = re.search(rf"{name}\s*=\s*(\d+)", HDR.read_text())
    assert m, name
    return int(m.group(1))


def test_header_phrase_is_c3_e3_g3_c4():
    assert _const("kNoteC3") == 60
    assert _const("kNoteE3") == 64
    assert _const("kNoteG3") == 67
    assert _const("kNoteC4") == 72
    assert _const("kPhraseNoteCount") == 4
    cpp = CPP.read_text()
    assert "kNoteC3, kNoteE3, kNoteG3, kNoteC4" in cpp
    assert "malloc" not in cpp
    assert "new " not in cpp


def test_replica_queue_emits_eight_events():
    """Mirror PhraseKernel trigger+render with a fixed array. No heap."""
    notes = (
        _const("kNoteC3"),
        _const("kNoteE3"),
        _const("kNoteG3"),
        _const("kNoteC4"),
    )
    gap = _const("kFramesBetweenNotes")
    length = _const("kNoteLengthFrames")
    cap = _const("kMaxQueuedEvents")
    queue = []
    for i, n in enumerate(notes):
        on_at = i * gap
        off_at = on_at + length
        queue.append((on_at, 0x90, n, 100))
        queue.append((off_at, 0x80, n, 0))
    assert len(queue) <= cap
    # Drain with a large frame count, same as render().
    out = [ev for ev in queue if ev[0] < 100000]
    ons = [ev[2] for ev in out if ev[1] == 0x90]
    offs = [ev[2] for ev in out if ev[1] == 0x80]
    assert ons == [60, 64, 67, 72]
    assert offs == [60, 64, 67, 72]
    assert len(out) == 8
