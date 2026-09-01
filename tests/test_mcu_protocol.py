"""MCU encode/decode. No live Logic. Mapping is EXPERIMENTAL."""

from __future__ import annotations

from logic_probe.mcu import (
    FADER_14_MAX,
    MCU_HDR,
    SurfaceState,
    db_to_fader14,
    echo_matches,
    fader14_to_db,
    fader_pitchbend_bytes,
    host_connection_query,
    parse_pitchbend,
    strip_for_track,
)


def test_strip_for_track_is_1_based_bank0():
    assert strip_for_track(1) == 0
    assert strip_for_track(3) == 2
    assert strip_for_track(8) == 7


def test_zero_db_is_three_quarter_throw():
    v = db_to_fader14(0.0)
    assert abs(v / FADER_14_MAX - 0.75) < 0.01
    assert abs(fader14_to_db(v)) < 0.05


def test_minus_6db_below_unity_and_roundtrip():
    v = db_to_fader14(-6.0)
    assert 0 < v < db_to_fader14(0.0)
    assert abs(fader14_to_db(v) - (-6.0)) < 0.15


def test_plus_6db_is_max():
    assert db_to_fader14(6.0) == FADER_14_MAX
    assert db_to_fader14(12.0) == FADER_14_MAX


def test_pitchbend_bytes_roundtrip():
    raw = fader_pitchbend_bytes(2, 6160)
    assert raw[0] == 0xE2
    parsed = parse_pitchbend(raw[0], raw[1], raw[2])
    assert parsed == (2, 6160)


def test_handshake_sysex_is_mcu_hdr():
    q = host_connection_query()
    assert q[0] == 0xF0 and q[-1] == 0xF7
    assert tuple(q[1:5]) == MCU_HDR
    assert q[5] == 0x01


def test_echo_match_tolerance():
    sent = db_to_fader14(-6.0)
    assert echo_matches(sent, sent, -6.0)
    assert echo_matches(sent, sent + 10, -6.0)
    assert not echo_matches(sent, 0, -6.0)


def test_surface_state_parses_fader_and_sysex():
    st = SurfaceState()
    st.handle(fader_pitchbend_bytes(2, 1000))
    st.handle(host_connection_query())
    assert st.saw_mcu
    assert st.fader[2] == 1000
