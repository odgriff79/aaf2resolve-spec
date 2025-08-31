from __future__ import annotations
import json
import subprocess
import sys
from typing import Any, Dict, List, Tuple

SAFE_COMMANDS: Dict[str, List[str]] = {
    "lint": ["ruff", "check", "."],
    "type_check": ["mypy", "."],
    "test": ["pytest", "-q"],
    "validate_json": ["python", "-m", "src.validate_canonical"],
    "ci": ["make", "ci"],
}

def run_safe(name: str) -> Tuple[int, str]:
    base = SAFE_COMMANDS.get(name)
    if not base:
        return (2, f"unknown tool: {name}")
    try:
        p = subprocess.run(base, capture_output=True, text=True, check=False)
        out = (p.stdout or "") + (p.stderr or "")
        return (p.returncode, out)
    except Exception as e:
        return (1, f"exec error: {e}")
