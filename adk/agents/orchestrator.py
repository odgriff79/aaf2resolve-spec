from __future__ import annotations

import json
import sys
from typing import Any, Dict

from adk.models.model_adapters import MultiProviderAgent
from adk.monitoring.status import update_status_safe


def main() -> int:
    agent = MultiProviderAgent()

    status_blob: Dict[str, Any] = {
        "orchestrator": "running",
        "models": agent.connectivity(dry_run=True),
        "timestamp": "2024-08-31",
    }

    update_status_safe("agent_status.json", status_blob)
    print(json.dumps(status_blob, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
