"""Live-Logic evals. Skip is not pass. AX receipts cannot be the pass bit."""

from __future__ import annotations

import pytest

from logic_probe.channels import mixer_set_volume
from logic_probe.envelope import SEMANTIC_STATUSES
from logic_probe.host import detect

pytestmark = pytest.mark.live_logic

EVALS_STUB = ("E01", "E02", "E03", "E04", "E05", "E07", "E08", "E09", "E10")


@pytest.mark.parametrize("eval_id", EVALS_STUB)
def test_live_eval_fail_closed_without_logic(eval_id: str):
    host = detect()
    if not host["logic_reachable"]:
        pytest.fail(
            f"{eval_id}: Logic Pro is not reachable ({host['reason']}). "
            "Skip is not pass. This eval remains UNKNOWN, not TESTED."
        )
    pytest.fail(
        f"{eval_id}: Logic process seen but this drop has no live harness "
        "implementation for this eval. Do not mint TESTED. Status remains UNKNOWN."
    )


def test_e06_mcu_fader_echo():
    host = detect()
    if not host["logic_reachable"]:
        pytest.fail(
            "E06: Logic Pro is not reachable (%s). Skip is not pass."
            % host["reason"]
        )
    env = mixer_set_volume(3, -6.0)
    assert env["channel"] == "mcu"
    assert env["status"] in SEMANTIC_STATUSES
    assert env["readback"] is None or env["readback"].get("method") != "ax_live"
    if env["status"] != "confirmed":
        pytest.fail(
            "E06 not confirmed (%s): %s. MCU echo is required. "
            "Do not mint TESTED. Status remains UNKNOWN."
            % (env["status"], env.get("verification"))
        )
    assert env["readback"]["method"] == "mcu_feedback"
