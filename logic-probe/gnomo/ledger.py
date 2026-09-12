"""Append-only decision ledger.

Why a ledger and not a chat log: a companion that decides has to be
auditable. studio/DECISION_LOG.md is the hand-written record of standing
decisions; this is the machine record of every call the gnome made, in the
same shape it printed at the time.

Write failures are reported, never swallowed. A decision that did not get
written down did not happen.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

REPO_ROOT = Path(__file__).resolve().parents[2]
LEDGER_PATH = REPO_ROOT / "studio" / "datasets" / "decisions.jsonl"


def append(record: dict[str, Any], *, path: Path | None = None) -> tuple[bool, str]:
    target = path or LEDGER_PATH
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError as exc:
        return False, f"ledger write failed: {exc}"
    return True, str(target)


def read(limit: int = 10, *, path: Path | None = None) -> list[dict[str, Any]]:
    target = path or LEDGER_PATH
    try:
        lines = target.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    out: list[dict[str, Any]] = []
    for line in lines[-limit:] if limit > 0 else lines:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def iter_all(*, path: Path | None = None) -> Iterator[dict[str, Any]]:
    yield from read(limit=0, path=path)
