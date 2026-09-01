"""Probe channels. MCU mixer writes attempt live IAC; AX stays a stub."""

from __future__ import annotations

from .envelope import confirmed, failed, uncertain
from .host import detect


def _base_notes(host: dict) -> list[str]:
    return [
        f"host.reason={host['reason']}",
        "confirmed is reserved for independent readback after a harness eval passes",
        "MELEGI stays aumi MIDI FX; mixer dB is an MCU fader, not AU pass-through",
    ]


def _cs_notes(cs: dict) -> list[str]:
    return [
        f"cs_prefs.exists={cs.get('exists')} magic={cs.get('magic')!r}",
        f"cs_catalog={cs.get('catalog')}",
        f"cs_named_ports={cs.get('named_ports')}",
        f"cs_installed_hints={cs.get('installed_hints')}",
        f"cs_iac_mentioned={cs.get('iac_mentioned')}",
        "Logic Control in the .cs catalog is the module list, not proof of an installed surface",
        "Installed CS observed: Logic Remote / iPad; SSL 2+ MIDI is in the blob but was CoreMIDI-offline",
        "Assign Mackie Control in Logic Pro > Control Surfaces > Setup: "
        "Input = IAC Driver logic-probe-mcu-cmd, Output = IAC Driver logic-probe-mcu-fb",
        "Do not Rebuild Defaults (destructive to existing iPad / SSL assignments)",
    ]


def mixer_set_volume(track: int, db: float) -> dict:
    host = detect()
    requested = {"track": track, "db": db}
    if not host["logic_reachable"]:
        return uncertain(
            probe_id="mixer_set_volume",
            channel="mcu",
            operation="track.set_volume",
            requested=requested,
            reason="channel_not_implemented_no_readback"
            if host["reason"] == "logic_process_seen_no_channel"
            else host["reason"],
            before={"db": None, "source": None, "fader14": None},
            logic_reachable=bool(host["logic_reachable"]),
            extra_notes=_base_notes(host) + ["E06 not passed without MCU echo"],
            logic_version=host.get("logic_version"),
            macos_version=host.get("macos_version"),
        )

    from . import cs_prefs, mcu, midi_io

    cs = cs_prefs.summarize()
    iac = midi_io.ensure_iac_mcu_buses()
    ports = midi_io.snapshot_ports()
    pair = midi_io.select_mcu_pair(ports)
    notes = _base_notes(host) + _cs_notes(cs) + [
        f"midi.inputs={ports.get('inputs')}",
        f"midi.outputs={ports.get('outputs')}",
        f"iac={iac}",
        "never send MCU pitch-bend to Logic Pro Virtual In (sequencer port, not CS)",
    ]
    versions = {
        "logic_version": host.get("logic_version"),
        "macos_version": host.get("macos_version"),
    }
    before = {"db": None, "source": None, "fader14": None}

    if pair is None:
        return uncertain(
            probe_id="mixer_set_volume",
            channel="mcu",
            operation="track.set_volume",
            requested=requested,
            reason="mcu_ports_not_found",
            adapter_success=False,
            before=before,
            logic_reachable=True,
            extra_notes=notes + ["E06 remains UNKNOWN until Mackie Control is assigned to the IAC buses"],
            **versions,
        )

    link = None
    try:
        link = midi_io.MidiLink(pair["cmd_out"], pair["fb_in"])
        result = mcu.run_set_volume(
            send=link.send,
            receive_pending=link.receive_pending,
            track=track,
            db=db,
        )
    except midi_io.MidiError as exc:
        return uncertain(
            probe_id="mixer_set_volume",
            channel="mcu",
            operation="track.set_volume",
            requested=requested,
            reason=str(exc),
            adapter_success=False,
            before=before,
            logic_reachable=True,
            extra_notes=notes,
            **versions,
        )
    except Exception as exc:  # noqa: BLE001
        return uncertain(
            probe_id="mixer_set_volume",
            channel="mcu",
            operation="track.set_volume",
            requested=requested,
            reason=f"mcu_io_error:{type(exc).__name__}:{exc}",
            adapter_success=False,
            before=before,
            logic_reachable=True,
            extra_notes=notes,
            **versions,
        )
    finally:
        if link is not None:
            try:
                link.close()
            except Exception:
                pass

    notes.extend(result.get("notes") or [])
    notes.append(f"mcu_pair={pair}")
    notes.append(f"strip={result.get('strip')} bank_assumed={result.get('bank_assumed')}")
    notes.append(f"saw_mcu={result.get('saw_mcu')} msg_count={result.get('msg_count')}")
    if result.get("before14") is not None:
        before = {
            "db": mcu.fader14_to_db(result["before14"]),
            "source": "mcu_feedback",
            "fader14": result["before14"],
        }
    adapter = {
        "success": True,
        "reason": "mcu_fader_sent",
        "cmd_out": pair["cmd_out"],
        "fb_in": pair["fb_in"],
        "sent14": result["sent14"],
        "strip": result["strip"],
    }

    if result["matched"] and result["saw_mcu"]:
        readback = {
            "method": "mcu_feedback",
            "fader14": result["echo14"],
            "observed_db": result["echo_db"],
            "msg_count": result["msg_count"],
        }
        return confirmed(
            probe_id="mixer_set_volume",
            channel="mcu",
            operation="track.set_volume",
            requested=requested,
            before=before,
            adapter_result=adapter,
            readback=readback,
            extra_notes=notes,
            **versions,
        )

    if result["saw_mcu"] and result["echo14"] is not None:
        readback = {
            "method": "mcu_feedback",
            "fader14": result["echo14"],
            "observed_db": result["echo_db"],
            "msg_count": result["msg_count"],
        }
        return failed(
            probe_id="mixer_set_volume",
            channel="mcu",
            operation="track.set_volume",
            requested=requested,
            reason="mcu_echo_mismatch",
            before=before,
            adapter_result=adapter,
            readback=readback,
            extra_notes=notes,
            **versions,
        )

    return uncertain(
        probe_id="mixer_set_volume",
        channel="mcu",
        operation="track.set_volume",
        requested=requested,
        reason="mcu_no_echo",
        adapter_success=True,
        before=before,
        logic_reachable=True,
        extra_notes=notes
        + [
            "bytes left this process on IAC cmd; Logic did not echo MCU on fb",
            "most likely: no Mackie Control / Logic Control surface assigned to those IAC ports",
            "E06 remains UNKNOWN (skip is not pass)",
        ],
        **versions,
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
