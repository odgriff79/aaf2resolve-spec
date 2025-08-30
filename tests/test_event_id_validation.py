from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _run(json_path: str, tmp: Path) -> dict:
    out = tmp / "report.json"
    p = subprocess.run(
        [sys.executable, "-m", "src.validate_canonical", "--report", str(out), json_path],
        capture_output=True,
        text=True,
    )
    assert p.returncode in (0, 1, 2), f"rc={p.returncode}\nSTDERR:\n{p.stderr}"
    return json.loads(out.read_text(encoding="utf-8"))


def _codes(rep: dict) -> set[str]:
    return {e.get("code", "") for e in (rep.get("errors") or []) if isinstance(e, dict)}


def test_invalid_event_id_alpha(tmp_path: Path) -> None:
    rep = _run("tests/samples/invalid_event_id_alpha.json", tmp_path)
    assert rep.get("ok") is False
    assert "CANON-REQ-020" in _codes(rep)


def test_invalid_event_id_short(tmp_path: Path) -> None:
    rep = _run("tests/samples/invalid_event_id_short.json", tmp_path)
    assert rep.get("ok") is False
    assert "CANON-REQ-020" in _codes(rep)
