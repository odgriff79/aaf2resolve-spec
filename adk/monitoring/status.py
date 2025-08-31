from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

MON_DIR = Path("adk/monitoring")
MON_DIR.mkdir(parents=True, exist_ok=True)


def update_status_safe(filename: str, status_data: Dict[str, Any]) -> Path:
    """Atomically write status JSON into adk/monitoring/."""
    tmp = MON_DIR / f".{filename}.tmp"
    final = MON_DIR / filename
    tmp.write_text(json.dumps(status_data, indent=2), encoding="utf-8")
    os.replace(tmp, final)
    return final
