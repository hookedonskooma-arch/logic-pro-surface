"""Mackie Control / Logic Control MIDI bytes.

Apple documents that Logic hosts MCU-class surfaces. Apple does not publish
this byte protocol. Mapping below is from Mackie/Logic Control MIDI maps and
community virtual-MCU work. Tag: EXPERIMENTAL. Not a first-party Logic API.
"""

from __future__ import annotations

import math
import time
from typing import Any, Iterable

# Mackie manufacturer + MCU device id (0x14 = Mackie Control Universal).
MCU_HDR = (0x00, 0x00, 0x66, 0x14)
HS_DEVICE_QUERY = 0x00
HS_CONN_QUERY = 0x01
HS_CONN_REPLY = 0x02
HS_CONN_CONFIRM = 0x03
# 7-byte serial + 4-byte challenge (MCU host-connection query payload).
SERIAL = b"LPROBE1"
CHALLENGE = bytes((0x01, 0x02, 0x03, 0x04))

# Channel-strip buttons / fader touch (MCU MIDI map).
NOTE_BANK_LEFT = 0x2E
NOTE_BANK_RIGHT = 0x2F
NOTE_CHANNEL_LEFT = 0x30
NOTE_CHANNEL_RIGHT = 0x31
FADER_TOUCH_BASE = 0x68  # + strip 0..8 (8 = master)
NOTE_PLAY = 0x5E
NOTE_STOP = 0x5D

FADER_14_MIN = 0
FADER_14_MAX = 16383
# Logic's mixer tops out at +6 dB. 0 dB sits at 3/4 fader travel on the
# Logic overlay (not the Pro Tools overlay where 0 dB is mid-throw).
FADER_POS_0DB = 0.75
FADER_DB_MAX = 6.0
FADER_DB_FLOOR = -144.0

# Echo match: 14-bit counts (~1.6% of throw) or dB. Either is enough.
FADER_ECHO_COUNTS = 256
FADER_ECHO_DB = 1.5


def clamp_fader14(value: int) -> int:
    return max(FADER_14_MIN, min(FADER_14_MAX, int(value)))


def db_to_fader14(db: float) -> int:
    """EXPERIMENTAL Logic-shaped fader law. Not an Apple spec.

    pos 0..1, 0.75 = 0 dB, 1.0 = +6 dB. Below 0 dB: 20*log10(pos/0.75).
    """
    if db >= FADER_DB_MAX:
        return FADER_14_MAX
    if db <= FADER_DB_FLOOR:
        return FADER_14_MIN
    if db >= 0.0:
        pos = FADER_POS_0DB + (db / FADER_DB_MAX) * (1.0 - FADER_POS_0DB)
    else:
        pos = FADER_POS_0DB * (10.0 ** (db / 20.0))
    return clamp_fader14(round(pos * FADER_14_MAX))


def fader14_to_db(value14: int) -> float:
    pos = clamp_fader14(value14) / float(FADER_14_MAX)
    if pos <= 0.0:
        return FADER_DB_FLOOR
    if pos >= 1.0:
        return FADER_DB_MAX
    if pos >= FADER_POS_0DB:
        return ((pos - FADER_POS_0DB) / (1.0 - FADER_POS_0DB)) * FADER_DB_MAX
    return 20.0 * math.log10(pos / FADER_POS_0DB)


def fader_pitchbend_bytes(strip: int, value14: int) -> list[int]:
    v = clamp_fader14(value14)
    return [0xE0 | (strip & 0x0F), v & 0x7F, (v >> 7) & 0x7F]


def parse_pitchbend(status: int, lsb: int, msb: int) -> tuple[int, int] | None:
    if (status & 0xF0) != 0xE0:
        return None
    return status & 0x0F, (msb << 7) | lsb


def sysex(cmd: int, payload: bytes) -> list[int]:
    return [0xF0, *MCU_HDR, cmd, *payload, 0xF7]


def host_connection_query() -> list[int]:
    return sysex(HS_CONN_QUERY, SERIAL + CHALLENGE)


def host_connection_confirm() -> list[int]:
    return sysex(HS_CONN_CONFIRM, SERIAL)


def is_mcu_sysex(msg: list[int]) -> bool:
    return len(msg) >= 7 and msg[0] == 0xF0 and tuple(msg[1:5]) == MCU_HDR


def sysex_cmd(msg: list[int]) -> int | None:
    if not is_mcu_sysex(msg):
        return None
    return msg[5]


def echo_matches(sent14: int, echo14: int | None, requested_db: float) -> bool:
    if echo14 is None:
        return False
    if abs(echo14 - sent14) <= FADER_ECHO_COUNTS:
        return True
    return abs(fader14_to_db(echo14) - requested_db) <= FADER_ECHO_DB


def strip_for_track(track: int) -> int:
    """1-based track number -> MCU strip assuming bank 0 (tracks 1..8)."""
    if track < 1:
        raise ValueError("track is 1-based")
    return (track - 1) % 8


class SurfaceState:
    def __init__(self) -> None:
        self.fader = [0] * 9
        self.saw_mcu = False
        self.sysex_cmds: list[int] = []
        self.msg_count = 0

    def handle(self, raw: list[int]) -> None:
        if not raw:
            return
        self.msg_count += 1
        st = raw[0]
        if st == 0xF0:
            cmd = sysex_cmd(raw)
            if cmd is not None:
                self.saw_mcu = True
                self.sysex_cmds.append(cmd)
            return
        if (st & 0xF0) == 0xE0 and len(raw) >= 3:
            parsed = parse_pitchbend(st, raw[1], raw[2])
            if parsed is not None:
                ch, val = parsed
                if ch < len(self.fader):
                    self.fader[ch] = val
                    self.saw_mcu = True


def _raw_of(msg: Any) -> list[int]:
    if hasattr(msg, "bytes"):
        return list(msg.bytes())
    if isinstance(msg, (list, tuple)):
        return [int(x) for x in msg]
    return []


def run_set_volume(
    *,
    send,
    receive_pending,
    track: int,
    db: float,
    settle_s: float = 0.55,
    echo_s: float = 0.9,
    bank_home: bool = True,
) -> dict[str, Any]:
    """Talk MCU. `send(list[int])`; `receive_pending()` -> iterable of raw msgs.

    Does not mint confirmed. Caller wraps the envelope.
    """
    state = SurfaceState()
    notes: list[str] = [
        "MCU byte protocol is EXPERIMENTAL (not an Apple spec)",
        "same-bus IAC loopback is not independent readback",
        "AX receipts cannot be the pass bit",
    ]

    def drain(seconds: float) -> None:
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            batch = list(receive_pending() or [])
            if not batch:
                time.sleep(0.004)
                continue
            for msg in batch:
                raw = _raw_of(msg)
                state.handle(raw)
                cmd = sysex_cmd(raw)
                if cmd == HS_DEVICE_QUERY:
                    send(host_connection_query())
                elif cmd == HS_CONN_REPLY:
                    send(host_connection_confirm())

    send(host_connection_query())
    drain(settle_s)

    if bank_home:
        for _ in range(8):
            send([0x90, NOTE_BANK_LEFT, 127])
            time.sleep(0.015)
            send([0x80, NOTE_BANK_LEFT, 0])
        drain(0.25)

    before14 = state.fader[strip_for_track(track)] if state.saw_mcu else None
    strip = strip_for_track(track)
    sent14 = db_to_fader14(db)

    send([0x90, FADER_TOUCH_BASE + strip, 127])
    time.sleep(0.02)
    send(fader_pitchbend_bytes(strip, sent14))
    time.sleep(0.02)
    send([0x80, FADER_TOUCH_BASE + strip, 0])
    drain(echo_s)

    echo14: int | None = state.fader[strip] if state.saw_mcu else None
    matched = echo_matches(sent14, echo14, db) and state.saw_mcu
    return {
        "strip": strip,
        "sent14": sent14,
        "sent_db_law": fader14_to_db(sent14),
        "before14": before14,
        "echo14": echo14,
        "echo_db": None if echo14 is None or not state.saw_mcu else fader14_to_db(echo14),
        "saw_mcu": state.saw_mcu,
        "msg_count": state.msg_count,
        "sysex_cmds": list(state.sysex_cmds),
        "matched": matched,
        "notes": notes,
        "bank_assumed": 0 if track <= 8 else (track - 1) // 8,
    }
