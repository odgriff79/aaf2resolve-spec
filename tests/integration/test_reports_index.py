from pathlib import Path
import json
import glob

def test_build_reports_index():
    reports_dir = Path("reports/integration")
    reports_dir.mkdir(parents=True, exist_ok=True)

    report_files = sorted(glob.glob(str(reports_dir / "*.report.json")))
    assert report_files, "No *.report.json files found to index in reports/integration/"

    entries = []
    totals = {"tests": 0, "ok": 0, "fail": 0}
    for rf in report_files:
        try:
            data = json.loads(Path(rf).read_text(encoding="utf-8"))
        except Exception:
            # If a report is malformed, mark as failed entry
            entries.append({"file": rf, "parse_ok": False, "ok": False})
            totals["tests"] += 1
            totals["fail"] += 1
            continue

        # Normalize expected shape
        test_name = data.get("test") or Path(rf).stem
        summary = data.get("summary") or {}
        ok = bool(summary.get("ok", False))

        entries.append({
            "file": rf,
            "test": test_name,
            "ok": ok,
            "version": summary.get("version"),
            "root_ok": summary.get("root_ok"),
            "has_library": summary.get("has_library"),
            "has_event": summary.get("has_event"),
            "has_project": summary.get("has_project"),
            "has_sequence": summary.get("has_sequence"),
            "has_spine": summary.get("has_spine"),
            "counts": summary.get("counts", {}),
        })

        totals["tests"] += 1
        totals["ok"] += 1 if ok else 0
        totals["fail"] += 0 if ok else 1

    index = {"totals": totals, "reports": entries}
    out_path = reports_dir / "index.json"
    out_path.write_text(json.dumps(index, indent=2), encoding="utf-8")

    # Assert the index exists and basic totals make sense
    assert out_path.exists(), "Expected reports/integration/index.json to be written"
    assert totals["tests"] == len(report_files), "Index totals mismatch number of reports"
