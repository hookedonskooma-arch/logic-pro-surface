import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(autouse=True)
def _offline_unless_live(request, monkeypatch):
    """Unit tests must not actuate a live Logic session."""
    if request.node.get_closest_marker("live_logic"):
        monkeypatch.delenv("LOGIC_PROBE_FORCE_OFFLINE", raising=False)
        return
    monkeypatch.setenv("LOGIC_PROBE_FORCE_OFFLINE", "1")


# Live-Logic evals can only fail off macOS. A plain `pytest` on Linux deselects
# them and says so loudly; they stay UNKNOWN, never pass. On macOS, or with an
# explicit -m, they run and fail closed as before.
_live_deselected: list[str] = []


def pytest_collection_modifyitems(config, items):
    if sys.platform == "darwin" or config.getoption("markexpr"):
        return
    keep = []
    for item in items:
        (_live_deselected if item.get_closest_marker("live_logic") else keep).append(item)
    if _live_deselected:
        config.hook.pytest_deselected(items=list(_live_deselected))
        items[:] = keep


def pytest_terminal_summary(terminalreporter):
    if _live_deselected:
        terminalreporter.write_sep(
            "!",
            f"{len(_live_deselected)} live Logic evals NOT RUN (not macOS): UNKNOWN, not TESTED",
            yellow=True,
        )
