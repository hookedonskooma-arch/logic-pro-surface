"""v0 channels: detect only. No MCU / AX / CoreMIDI actuation implemented."""

from __future__ import annotations

from .envelope import uncertain
from .host import detect


def _base_notes(host: dict) -> list[str]:
    return [
        f"host.reason={host['reason']}",
        "v0 implements envelopes, not MCU/AX/CoreMIDI writes",
        "confirmed is reserved for independent readback after a harness eval passes",
    ]


def mixer_set_volume(track: int, db: float) -> dict:
    host = detect()
    return uncertain(
        probe_id="mixer_set_volume",
        channel="mcu",
        operation="track.set_volume",
        requested={"track": track, "db": db},
        reason="channel_not_implemented_no_readback" if host["logic_reachable"] else host["reason"],
        before={"db": None, "source": None},
        logic_reachable=bool(host["logic_reachable"]),
        extra_notes=_base_notes(host) + ["E06 not passed in this drop"],
    )


def transport_play() -> dict:
    host = detect()
    return uncertain(
        probe_id="transport_play",
        channel="mcu",
        operation="transport.play",
        requested={"command": "play"},
        reason="channel_not_implemented_no_readback" if host["logic_reachable"] else host["reason"],
        before={"playing": None, "source": None},
        logic_reachable=bool(host["logic_reachable"]),
        extra_notes=_base_notes(host) + ["E05 not passed in this drop"],
    )


def ax_inspect_selected_track() -> dict:
    host = detect()
    # AX is a workaround channel. Even with Logic running, v0 does not walk the tree
    # and will not mint confirmed from a missing inspection.
    return uncertain(
        probe_id="ax_inspect_selected_track",
        channel="accessibility",
        operation="ax.inspect_selected_track",
        requested={"target": "selected_track"},
        reason="ax_not_implemented_no_tree" if host["logic_reachable"] else host["reason"],
        before={"selected_track": None, "source": None},
        logic_reachable=bool(host["logic_reachable"]),
        extra_notes=_base_notes(host)
        + [
            "Accessibility is not a public Logic API",
            "AX receipts cannot be the pass bit",
            "never fake confirmed for ax inspect",
        ],
    )
