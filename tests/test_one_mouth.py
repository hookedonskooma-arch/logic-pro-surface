"""One mouth, enforced by the build rather than by a document.

Decision 004 said there is one mouth. Three days later a second `say` call
appeared in chatbot/voice.py, because "one mouth" was only a convention and
the implementation lived in a script nobody could import.

These tests make it structural. A fourth mouth fails CI.
"""

from __future__ import annotations

import re

import pytest

from voz import mouth

# Anything that shells out to `say` outside voz/ is a second mouth.
#
# Matches invocation only: `shutil.which("say")`, or "say" as the first element
# of an argv list. The bare string "say" is fine - it is a CLI subcommand name
# in gnomo/cli.py, not a second mouth. A guard that cries wolf gets deleted.
SAY_CALL = re.compile(r"""shutil\.which\(\s*["']say["']|\[\s*["']say["']""")

SEARCH_ROOTS = ("logic-probe", "scripts", "chatbot", "studio")
ALLOWED = ("logic-probe/voz/mouth.py",)


def _python_files(repo_root):
    for root in SEARCH_ROOTS:
        base = repo_root / root
        if not base.is_dir():
            continue
        for path in base.rglob("*.py"):
            if ".venv" in path.parts or "__pycache__" in path.parts:
                continue
            yield path


def test_only_voz_invokes_say(repo_root):
    """The rule that regrew as a convention now fails the build instead."""
    offenders = []
    for path in _python_files(repo_root):
        rel = path.relative_to(repo_root).as_posix()
        if rel in ALLOWED:
            continue
        if SAY_CALL.search(path.read_text(encoding="utf-8")):
            offenders.append(rel)
    assert not offenders, (
        f"these call `say` directly instead of importing voz.mouth: {offenders}. "
        "A second mouth loses the lexicon, the secret filter and the spoken log."
    )


def test_speak_script_holds_no_second_implementation(repo_root):
    """scripts/speak.py is a CLI. The logic must not live there again."""
    body = (repo_root / "scripts" / "speak.py").read_text()
    assert "from voz import mouth" in body
    for leaked in ("LEXICON", "PREFERRED_VOICES", "_SECRET_MARKERS"):
        assert leaked not in body, f"{leaked} belongs in voz.mouth, not the CLI"


def test_lexicon_is_applied_to_logic_vocabulary():
    """Fluency here means Logic vocabulary spoken correctly."""
    spoken = mouth.apply_lexicon("the AU sends MCU over IAC using aumi and AUv3")
    for expected in ("A U", "M C U", "I A C", "A U M I", "A U v 3"):
        assert expected in spoken, expected
    assert "aumi" not in spoken.lower()


@pytest.mark.parametrize(
    "secret",
    ["my api_key is 123", "Bearer abcdef", "sk-live-xyz", "password hunter2"],
)
def test_secrets_are_never_logged(secret):
    assert mouth.should_skip_log(secret) is not None


def test_ordinary_speech_is_loggable():
    assert mouth.should_skip_log("MCU echo is the pass bit") is None
