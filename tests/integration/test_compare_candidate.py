from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path

import pytest


CSV_PATH = Path("tests/fixtures/aaf/candidate_legacy.csv")
CANONICAL_PATH = Path("reports/integration/candidate_from_aaf.canonical.json")
REPORT_PATH = Path("reports/integration/candidate_compare.report.json")


def _parse_summary_and_events(csv_text: str) -> tuple[dict, int]:
    lines = csv_text.splitlines()
    # ---- Summary (Timeline Summary preamble)
    name = None
    rate = None
    start = None

    summary_mode = False
    for line in lines:
        if not summary_mode and line.strip().lower().startswith("timeline summary"):
            summary_mode = True
            continue
        if summary_mode:
            if not line.strip():  # blank ends summary
                break
            if "," in line:
                k, v = line.split(",", 1)
                k = k.strip().lower()
                v = v.strip()
                if k == "timeline name":
                    name = v
                elif k == "timeline edit rate":
                    m = re.match(r"([0-9]+(?:\.[0-9]+)?)", v)
                    if m:
                        rv = float(m.group(1))
                        rate = int(rv) if rv.is_integer() else rv
                elif k == "timeline start":
                    start = v

    # ---- Event table (first line starting with Event,)
    header_idx = None
    for i, line in enumerate(lines):
        if line.startswith("Event,"):
            header_idx = i
            break
    if header_idx is None:
        raise AssertionError("Could not find 'Event,' header row in CSV.")

    table_text = "\n".join(lines[header_idx:])
    reader = csv.DictReader(io.StringIO(table_text), delimiter=",")
    rows = list(reader)
    # Count rows with any timings (conservative)
    def has_timings(row: dict) -> bool:
        return bool((row.get("Timeline Start TC") or row.get("StartTime")) and (row.get("End Time") or row.get("EndTime")))
    event_count = sum(1 for r in rows if any(r.values()) and has_timings(r))

    return {"name": name, "rate": rate, "start": start}, event_count


def test_compare_candidate_legacy_vs_canonical():
    # Precondition: artifacts exist (created by prior step)
    assert CSV_PATH.exists(), f"Missing CSV fixture at {CSV_PATH}"
    assert CANONICAL_PATH.exists(), f"Missing canonical JSON at {CANONICAL_PATH} (run the pipeline step first)"

    csv_text = CSV_PATH.read_text(encoding="utf-8", errors="replace")
    summary, csv_events = _parse_summary_and_events(csv_text)

    canonical = json.loads(CANONICAL_PATH.read_text(encoding="utf-8"))
    tl = canonical.get("timeline", {})
    clips = (tl.get("tracks") or [{}])[0].get("clips") or []
    can_name = tl.get("name")
    can_rate = tl.get("rate")
    can_start = tl.get("start")
    can_events = len(clips)

    checks = {
        "name": {"ok": can_name == summary["name"], "canonical": can_name, "csv": summary["name"]},
        "rate": {"ok": can_rate == summary["rate"], "canonical": can_rate, "csv": summary["rate"]},
        "start": {"ok": can_start == summary["start"], "canonical": can_start, "csv": summary["start"]},
        "event_count": {"ok": can_events == csv_events, "canonical": can_events, "csv": csv_events},
    }
    overall_ok = all(item["ok"] for item in checks.values())

    report = {
        "test": "candidate_compare",
        "csv": str(CSV_PATH),
        "canonical": str(CANONICAL_PATH),
        "summary": summary,
        "results": checks,
        "ok": overall_ok,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    assert overall_ok, f"Mismatch:\n{json.dumps(report, indent=2)}"
