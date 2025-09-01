from __future__ import annotations

import glob
import json
from datetime import datetime, timezone
from pathlib import Path


def test_build_reports_index() -> None:
    reports_dir = Path("reports/integration")
    reports = sorted(glob.glob(str(reports_dir / "*.report.json")))

    out: dict = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "totals": {"tests": 0, "ok": 0, "fail": 0},
        "reports": [],
    }

    for rep in reports:
        p = Path(rep)
        data = json.loads(p.read_text(encoding="utf-8"))

        summary = (data.get("summary") or {}) if isinstance(data, dict) else {}
        # Generic rule: if a report declares "ok", trust it; otherwise default False.
        if isinstance(data, dict) and "ok" in data:
            item_ok = bool(data["ok"])  # trust report-provided ok
        else:
            # derive from FCPXML summary when available
            item_ok = bool(
                summary.get("version") == "1.13"
                and summary.get("root_ok") is True
                and summary.get("has_library") is True
                and summary.get("has_event") is True
                and summary.get("has_project") is True
                and summary.get("has_sequence") is True
                and summary.get("has_spine") is True
            )
item = {
            "file": str(p),
            "test": data.get("test") or p.stem if isinstance(data, dict) else p.stem,
            "ok": item_ok,
            # Keep FCPXML-specific fields when present (they'll be null for non-shape reports)
            "version": summary.get("version"),
            "root_ok": summary.get("root_ok"),
            "has_library": summary.get("has_library"),
            "has_event": summary.get("has_event"),
            "has_project": summary.get("has_project"),
            "has_sequence": summary.get("has_sequence"),
            "has_spine": summary.get("has_spine"),
            "counts": summary.get("counts", {}),
        }
        out["reports"].append(item)

    out["totals"]["tests"] = len(out["reports"])
    out["totals"]["ok"] = sum(1 for r in out["reports"] if r.get("ok"))
    out["totals"]["fail"] = out["totals"]["tests"] - out["totals"]["ok"]

    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "index.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
