"""GNOMO's hands: the ladder decides, a person says "Do it", and receipts stay receipts.

The Swift helper only runs on a Mac with a human at the dialog, so these tests
stand a fake helper in its place and check the Python half: what reaches the
helper, what never does, and how its replies are reported.
"""

from __future__ import annotations

import json
import stat
import sys
from pathlib import Path

import pytest

from gnomo import hands, ledger, mouth
from gnomo.cli import main as gnomo_main
from gnomo.ladder import TIER_ACT, TIER_REFUSE


@pytest.fixture
def fake_helper(tmp_path, monkeypatch):
    """A stand-in helper that records its argv and prints a scripted reply."""
    calls = tmp_path / "calls.jsonl"
    reply = tmp_path / "reply.json"
    reply.write_text(json.dumps({"ok": True, "status": "attempted", "channel": "ax_press",
                                 "app": "Logic Pro", "target": {"label": "Bounce"}}))
    script = tmp_path / "gnomo-hands"
    script.write_text(
        f"#!{sys.executable}\n"
        "import json, sys\n"
        f"open({str(calls)!r}, 'a').write(json.dumps(sys.argv[1:]) + '\\n')\n"
        f"print(open({str(reply)!r}).read())\n"
    )
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("GNOMO_HANDS_BIN", str(script))
    monkeypatch.setattr(hands.sys, "platform", "darwin")

    def argv_seen() -> list[list[str]]:
        if not calls.exists():
            return []
        return [json.loads(line) for line in calls.read_text().splitlines()]

    return {"reply": reply, "calls": argv_seen}


# --- authority ------------------------------------------------------------


@pytest.mark.parametrize("verb,target", [("look", ""), ("find", "Bounce"), ("point", "Delete Track")])
def test_observing_is_tier0_and_needs_no_yes(verb, target):
    d = hands.authorize(verb, target)
    assert d["tier"] == TIER_ACT
    assert d["hands"]["runs"] is True
    assert d["hands"]["human_yes"].startswith("not needed")


@pytest.mark.parametrize("verb,target", [("click", "Bounce"), ("type", "hello"), ("key", "cmd+z")])
def test_acting_always_requires_the_human_dialog(verb, target):
    d = hands.authorize(verb, target)
    assert d["hands"]["runs"] is True
    assert d["hands"]["human_yes"].startswith("required")


@pytest.mark.parametrize(
    "verb,target",
    [("click", "Rebuild Defaults"), ("type", "fake the loudness to -9 LUFS"), ("point", "rebuild defaults")],
)
def test_never_is_refused_before_the_helper(verb, target, fake_helper):
    d = hands.run(verb, target)
    assert d["tier"] == TIER_REFUSE
    assert d["hands"]["runs"] is False
    assert d["result"]["reason"] == "refused_by_ladder"
    assert fake_helper["calls"]() == []


def test_unknown_verb_and_missing_target_are_errors():
    with pytest.raises(ValueError):
        hands.authorize("drag", "x")
    with pytest.raises(ValueError):
        hands.authorize("click", "  ")


def test_no_skip_flag_exists():
    """There is no Python-side way to approve on the human's behalf."""
    import inspect

    params = set(inspect.signature(hands.run).parameters)
    assert params == {"verb", "target", "index"}


# --- running the helper ---------------------------------------------------


def test_off_macos_nothing_runs(monkeypatch, fake_helper):
    monkeypatch.setattr(hands.sys, "platform", "linux")
    d = hands.run("click", "Bounce")
    assert d["result"]["reason"] == "not_macos"
    assert fake_helper["calls"]() == []


def test_missing_helper_says_how_to_build(monkeypatch, tmp_path):
    monkeypatch.setattr(hands.sys, "platform", "darwin")
    monkeypatch.setenv("GNOMO_HANDS_BIN", str(tmp_path / "nope"))
    d = hands.run("look")
    assert d["result"]["reason"] == "helper_not_built"
    assert hands.BUILD_HINT in d["result"]["fix"]


def test_click_passes_label_and_index(fake_helper):
    d = hands.run("click", "Bounce", index=1)
    assert fake_helper["calls"]() == [["click", "Bounce", "--index", "1"]]
    assert d["result"]["status"] == "attempted"
    assert d["result"]["channel"] == "ax_press"


def test_helper_never_gets_to_say_confirmed(fake_helper):
    fake_helper["reply"].write_text(json.dumps({"ok": True, "status": "confirmed", "channel": "ax_press"}))
    assert hands.run("click", "Bounce")["result"]["status"] == "attempted"


def test_garbage_from_helper_is_uncertain(fake_helper):
    fake_helper["reply"].write_text("not json at all")
    r = hands.run("look")["result"]
    assert r["status"] == "uncertain"
    assert r["reason"] == "helper_bad_output"


def test_human_decline_is_reported(fake_helper):
    fake_helper["reply"].write_text(json.dumps({"ok": False, "status": "failed", "reason": "declined_by_human"}))
    assert hands.run("key", "cmd+z")["result"]["reason"] == "declined_by_human"


# --- CLI ------------------------------------------------------------------


def test_cli_hands_writes_ledger_and_speaks_receipt(capsys, monkeypatch, tmp_path, fake_helper):
    monkeypatch.setenv(mouth.MUTE_ENV, "1")
    log = tmp_path / "decisions.jsonl"
    monkeypatch.setattr(ledger, "LEDGER_PATH", log)
    assert gnomo_main(["--json", "hands", "click", "Bounce"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "hands"
    assert "receipt, not proof" in payload["spoken"]
    row = json.loads(Path(log).read_text().splitlines()[-1])
    assert row["hands"]["verb"] == "click" and row["result"]["status"] == "attempted"


def test_cli_hands_refusal_is_logged_too(capsys, monkeypatch, tmp_path, fake_helper):
    monkeypatch.setenv(mouth.MUTE_ENV, "1")
    log = tmp_path / "decisions.jsonl"
    monkeypatch.setattr(ledger, "LEDGER_PATH", log)
    assert gnomo_main(["--json", "hands", "click", "Rebuild", "Defaults"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["tier"] == TIER_REFUSE
    assert payload["spoken"].startswith("No.")
    assert json.loads(log.read_text().splitlines()[-1])["result"]["reason"] == "refused_by_ladder"
    assert fake_helper["calls"]() == []
