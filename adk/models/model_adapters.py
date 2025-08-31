from __future__ import annotations

import os
from typing import Any, Dict


class MultiProviderAgent:
    def __init__(self) -> None:
        self.env_ok = {
            "GOOGLE_API_KEY": bool(os.environ.get("GOOGLE_API_KEY")),
            "ANTHROPIC_API_KEY": bool(os.environ.get("ANTHROPIC_API_KEY")),
            "OPENAI_API_KEY": bool(os.environ.get("OPENAI_API_KEY")),
        }

    def connectivity(self, dry_run: bool = True) -> Dict[str, Any]:
        summary: Dict[str, Any] = {"env": self.env_ok}
        if dry_run:
            summary["note"] = "dry-run (no external calls)"
        return summary
