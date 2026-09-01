"""Honest result envelope.

confirmed requires independent readback AND verification.passed.
v0 never invents Logic state: missing measurements are null.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

SEMANTIC_STATUSES = frozenset({"confirmed", "uncertain", "failed"})


class EnvelopeError(ValueError):
    pass


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_envelope(
    *,
    probe_id: str,
    channel: str,
    operation: str,
    requested: dict[str, Any],
    before: dict[str, Any] | None,
    adapter_result: dict[str, Any],
    readback: dict[str, Any] | None,
    verification: dict[str, Any],
    status: str,
    logic_version: str | None = None,
    macos_version: str | None = None,
    notes: list[str] | None = None,
) -> dict[str, Any]:
    status = status.lower()
    if status not in SEMANTIC_STATUSES:
        raise EnvelopeError(f"status must be one of {sorted(SEMANTIC_STATUSES)}, got {status!r}")

    verification = dict(verification)
    passed = bool(verification.get("passed"))

    if status == "confirmed":
        if not passed:
            raise EnvelopeError("confirmed requires verification.passed")
        if readback is None:
            raise EnvelopeError("confirmed requires independent readback")
        if readback.get("method") in {None, "none", "ax_live"}:
            raise EnvelopeError("confirmed cannot use missing or ax_live-only readback as the pass bit")

    envelope = {
        "probe_id": probe_id,
        "timestamp": utc_now_iso(),
        "logic_version": logic_version,
        "macos_version": macos_version,
        "channel": channel,
        "operation": operation,
        "requested": requested,
        "before": before,
        "adapter_result": adapter_result,
        "readback": readback,
        "verification": verification,
        "status": status,
        "notes": notes or [],
    }
    return envelope


def uncertain(
    *,
    probe_id: str,
    channel: str,
    operation: str,
    requested: dict[str, Any],
    reason: str,
    adapter_success: bool = False,
    before: dict[str, Any] | None = None,
    logic_reachable: bool = False,
    extra_notes: list[str] | None = None,
    logic_version: str | None = None,
    macos_version: str | None = None,
) -> dict[str, Any]:
    notes = [
        "skip is not pass",
        "sent command is not confirmed",
        "adapter success is not semantic success",
    ]
    if extra_notes:
        notes.extend(extra_notes)
    if not logic_reachable:
        notes.append("Logic Pro is not reachable from this process")
    return build_envelope(
        probe_id=probe_id,
        channel=channel,
        operation=operation,
        requested=requested,
        before=before,
        adapter_result={"success": adapter_success, "reason": reason},
        readback=None,
        verification={"passed": False, "reason": reason},
        status="uncertain",
        notes=notes,
        logic_version=logic_version,
        macos_version=macos_version,
    )



def failed(
    *,
    probe_id: str,
    channel: str,
    operation: str,
    requested: dict[str, Any],
    reason: str,
    before: dict[str, Any] | None = None,
    adapter_result: dict[str, Any] | None = None,
    readback: dict[str, Any] | None = None,
    extra_notes: list[str] | None = None,
    logic_version: str | None = None,
    macos_version: str | None = None,
) -> dict[str, Any]:
    notes = [
        "skip is not pass",
        "sent command is not confirmed",
        "adapter success is not semantic success",
    ]
    if extra_notes:
        notes.extend(extra_notes)
    return build_envelope(
        probe_id=probe_id,
        channel=channel,
        operation=operation,
        requested=requested,
        before=before,
        adapter_result=adapter_result or {"success": True, "reason": reason},
        readback=readback,
        verification={"passed": False, "reason": reason},
        status="failed",
        notes=notes,
        logic_version=logic_version,
        macos_version=macos_version,
    )


def confirmed(
    *,
    probe_id: str,
    channel: str,
    operation: str,
    requested: dict[str, Any],
    before: dict[str, Any],
    adapter_result: dict[str, Any],
    readback: dict[str, Any],
    extra_notes: list[str] | None = None,
    logic_version: str | None = None,
    macos_version: str | None = None,
) -> dict[str, Any]:
    """Independent readback required. ax_live is rejected by build_envelope."""
    notes = extra_notes or []
    return build_envelope(
        probe_id=probe_id,
        channel=channel,
        operation=operation,
        requested=requested,
        before=before,
        adapter_result=adapter_result,
        readback=readback,
        verification={"passed": True, "reason": "independent_readback_matched"},
        status="confirmed",
        notes=notes,
        logic_version=logic_version,
        macos_version=macos_version,
    )
