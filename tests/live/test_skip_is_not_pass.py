"""Live-Logic evals. Skip is not pass. AX receipts cannot be the pass bit."""

from __future__ import annotations

import pytest

from logic_probe.host import detect

pytestmark = pytest.mark.live_logic

EVALS = ("E01", "E02", "E03", "E04", "E05", "E06", "E07", "E08", "E09", "E10")


@pytest.mark.parametrize("eval_id", EVALS)
def test_live_eval_fail_closed_without_logic(eval_id: str):
    host = detect()
    if not host["logic_reachable"]:
        pytest.fail(
            f"{eval_id}: Logic Pro is not reachable ({host['reason']}). "
            "Skip is not pass. This eval remains UNKNOWN, not TESTED."
        )
    pytest.fail(
        f"{eval_id}: Logic process seen but this v0 drop has no live harness "
        "implementation. Do not mint TESTED. Status remains UNKNOWN."
    )
