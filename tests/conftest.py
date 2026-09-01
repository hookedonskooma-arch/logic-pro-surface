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
