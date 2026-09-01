"""CoreMIDI / IAC helpers for the MCU probe.

Non-destructive: may bring the IAC Driver online and add two named buses
(logic-probe-mcu-cmd, logic-probe-mcu-fb). Does not touch SSL 2+, does not
rename Bus 1, does not quit Logic, does not edit MELEGI.
"""

from __future__ import annotations

from ctypes import (
    CDLL,
    POINTER,
    byref,
    c_char_p,
    c_int32,
    c_long,
    c_ubyte,
    c_uint32,
    c_ulong,
    c_void_p,
    create_string_buffer,
)
from typing import Any, Callable, Iterable

CMD_ENTITY = "logic-probe-mcu-cmd"
FB_ENTITY = "logic-probe-mcu-fb"
IAC_DEVICE_NAME = "IAC Driver"
UTF8 = 0x08000100

# Never treat these as Mackie Control. They are Logic's sequencer virtual
# endpoints (musical MIDI), not a control-surface assignment.
FORBIDDEN_MCU_NAMES = (
    "logic pro virtual in",
    "logic pro virtual out",
)


class MidiError(RuntimeError):
    pass


def _mido():
    try:
        import mido  # type: ignore
    except ImportError as exc:
        raise MidiError("mido_not_installed") from exc
    return mido


def snapshot_ports() -> dict[str, list[str]]:
    try:
        mido = _mido()
    except MidiError:
        return {"inputs": [], "outputs": [], "error": "mido_not_installed"}  # type: ignore[dict-item]
    try:
        return {
            "inputs": list(mido.get_input_names()),
            "outputs": list(mido.get_output_names()),
        }
    except Exception as exc:  # noqa: BLE001 — fail closed into the envelope
        return {"inputs": [], "outputs": [], "error": f"midi_list_failed:{exc}"}  # type: ignore[dict-item]


def _is_forbidden(name: str) -> bool:
    return name.strip().lower() in FORBIDDEN_MCU_NAMES


def mido_name_for_entity(entity: str) -> str:
    return f"{IAC_DEVICE_NAME} {entity}"


def select_mcu_pair(ports: dict[str, list[str]]) -> dict[str, str] | None:
    """Pick cmd output + fb input. Distinct buses required for independence."""
    inputs = [n for n in ports.get("inputs") or [] if not _is_forbidden(n)]
    outputs = [n for n in ports.get("outputs") or [] if not _is_forbidden(n)]
    cmd = mido_name_for_entity(CMD_ENTITY)
    fb = mido_name_for_entity(FB_ENTITY)
    if cmd in outputs and fb in inputs and cmd != fb:
        return {"cmd_out": cmd, "fb_in": fb, "kind": "iac_two_bus"}
    # Named Mackie/Logic Control hardware pair (same name in + out is OK
    # for a physical MCU: echo is motor-position, not IAC loopback).
    for out_name in outputs:
        low = out_name.lower()
        if "mackie" in low or "logic control" in low:
            for in_name in inputs:
                il = in_name.lower()
                if "mackie" in il or "logic control" in il:
                    return {"cmd_out": out_name, "fb_in": in_name, "kind": "named_mackie"}
    return None


def _coremidi():
    cm = CDLL("/System/Library/Frameworks/CoreMIDI.framework/CoreMIDI")
    cf = CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
    cm.MIDIGetNumberOfDevices.restype = c_ulong
    cm.MIDIGetDevice.argtypes = [c_ulong]
    cm.MIDIGetDevice.restype = c_uint32
    cm.MIDIObjectGetStringProperty.argtypes = [c_uint32, c_void_p, POINTER(c_void_p)]
    cm.MIDIObjectGetStringProperty.restype = c_int32
    cm.MIDIObjectGetIntegerProperty.argtypes = [c_uint32, c_void_p, POINTER(c_int32)]
    cm.MIDIObjectGetIntegerProperty.restype = c_int32
    cm.MIDIObjectSetIntegerProperty.argtypes = [c_uint32, c_void_p, c_int32]
    cm.MIDIObjectSetIntegerProperty.restype = c_int32
    cm.MIDIDeviceGetNumberOfEntities.argtypes = [c_uint32]
    cm.MIDIDeviceGetNumberOfEntities.restype = c_ulong
    cm.MIDIDeviceGetEntity.argtypes = [c_uint32, c_ulong]
    cm.MIDIDeviceGetEntity.restype = c_uint32
    cm.MIDIDeviceAddEntity.argtypes = [
        c_uint32,
        c_void_p,
        c_ubyte,
        c_ulong,
        c_ulong,
        POINTER(c_uint32),
    ]
    cm.MIDIDeviceAddEntity.restype = c_int32
    cf.CFStringCreateWithCString.argtypes = [c_void_p, c_char_p, c_uint32]
    cf.CFStringCreateWithCString.restype = c_void_p
    cf.CFStringGetCString.argtypes = [c_void_p, c_char_p, c_long, c_uint32]
    cf.CFStringGetCString.restype = c_ubyte
    cf.CFRelease.argtypes = [c_void_p]
    return cm, cf


def _cf_name(cm, cf, obj: int, k_name) -> str | None:
    ref = c_void_p()
    cm.MIDIObjectGetStringProperty(obj, k_name, byref(ref))
    if not ref.value:
        return None
    buf = create_string_buffer(1024)
    cf.CFStringGetCString(ref, buf, 1024, UTF8)
    cf.CFRelease(ref)
    return buf.value.decode("utf-8", "replace")


def ensure_iac_mcu_buses() -> dict[str, Any]:
    """Bring IAC online and ensure cmd/fb entities exist. Idempotent."""
    info: dict[str, Any] = {
        "attempted": True,
        "iac_found": False,
        "iac_was_offline": None,
        "iac_online": False,
        "entities": [],
        "added": [],
        "error": None,
        "ssl2_plus_touched": False,
    }
    try:
        cm, cf = _coremidi()
    except OSError as exc:
        info["error"] = f"coremidi_unavailable:{exc}"
        return info
    k_name = c_void_p.in_dll(cm, "kMIDIPropertyName")
    k_offline = c_void_p.in_dll(cm, "kMIDIPropertyOffline")
    iac = None
    for i in range(cm.MIDIGetNumberOfDevices()):
        dev = cm.MIDIGetDevice(i)
        name = _cf_name(cm, cf, dev, k_name)
        if name == IAC_DEVICE_NAME:
            iac = dev
            break
    if iac is None:
        info["error"] = "iac_driver_device_not_found"
        return info
    info["iac_found"] = True
    off = c_int32()
    cm.MIDIObjectGetIntegerProperty(iac, k_offline, byref(off))
    info["iac_was_offline"] = bool(off.value)
    if off.value:
        rc = cm.MIDIObjectSetIntegerProperty(iac, k_offline, 0)
        if rc != 0:
            info["error"] = f"iac_enable_failed:{rc}"
            return info
    off = c_int32()
    cm.MIDIObjectGetIntegerProperty(iac, k_offline, byref(off))
    info["iac_online"] = off.value == 0
    nent = cm.MIDIDeviceGetNumberOfEntities(iac)
    entities = [_cf_name(cm, cf, cm.MIDIDeviceGetEntity(iac, j), k_name) for j in range(nent)]
    info["entities"] = entities
    for wanted in (FB_ENTITY, CMD_ENTITY):
        if wanted in entities:
            continue
        new_ent = c_uint32()
        cfname = cf.CFStringCreateWithCString(None, wanted.encode("utf-8"), UTF8)
        rc = cm.MIDIDeviceAddEntity(iac, cfname, 0, 1, 1, byref(new_ent))
        if rc != 0:
            info["error"] = f"iac_add_entity_failed:{wanted}:{rc}"
            return info
        info["added"].append(wanted)
    nent = cm.MIDIDeviceGetNumberOfEntities(iac)
    info["entities"] = [
        _cf_name(cm, cf, cm.MIDIDeviceGetEntity(iac, j), k_name) for j in range(nent)
    ]
    return info


class MidiLink:
    """Send bytes on cmd_out, poll bytes on fb_in."""

    def __init__(self, cmd_out: str, fb_in: str) -> None:
        mido = _mido()
        try:
            self._out = mido.open_output(cmd_out)
            self._inp = mido.open_input(fb_in)
        except Exception as exc:
            raise MidiError(f"open_failed:{exc}") from exc
        self.cmd_out = cmd_out
        self.fb_in = fb_in

    def send(self, raw: list[int]) -> None:
        import mido as _m

        self._out.send(_m.Message.from_bytes(raw))

    def receive_pending(self) -> Iterable[Any]:
        return list(self._inp.iter_pending())

    def close(self) -> None:
        try:
            self._out.close()
        finally:
            self._inp.close()
