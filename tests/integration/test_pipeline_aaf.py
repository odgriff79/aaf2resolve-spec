from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

import pytest

from src.write_fcpxml import write_fcpxml_from_canonical  # type: ignore

# Probe for aaf2 once (PyPI package is "pyaaf2", import name is "aaf2")
try:
    import aaf2  # noqa: F401
    HAS_AAF2 = True
except Exception:
    HAS_AAF2 = False

# Fixture locations
FIXTURE_DIR = Path("tests/fixtures/aaf")
AAF_PATH = FIXTURE_DIR / "candidate.aaf"
LEGACY_JSON_PATH = FIXTURE_DIR / "candidate_legacy.json"
LEGACY_CSV_PATH = FIXTURE_DIR / "candidate_legacy.csv"


def _maybe_load_legacy() -> dict | None:
    """Prefer JSON; fallback to CSV with a 'canonical_json'/'json'/'canonical' column."""
    if LEGACY_JSON_PATH.exists():
        return json.loads(LEGACY_JSON_PATH.read_text(encoding="utf-8"))

    if LEGACY_CSV_PATH.exists():
        with LEGACY_CSV_PATH.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                blob = row.get("canonical_json") or row.get("json") or row.get("canonical")
                if blob:
                    try:
                        return json.loads(blob)
                    except Exception:
                        continue
    return None


def _shallow_compare(a: dict | None, b: dict | None) -> dict | None:
    if a is None or b is None:
        return None
    result = {"match": True, "checks": {}}
    keys = ["name", "rate", "start"]
    ta = a.get("timeline", {}) if isinstance(a, dict) else {}
    tb = b.get("timeline", {}) if isinstance(b, dict) else {}
    for k in keys:
        av = ta.get(k)
        bv = tb.get(k)
        ok = av == bv
        result["checks"][k] = {"ok": ok, "actual": av, "expected": bv}
        if not ok:
            result["match"] = False
    return result


def test_pipeline_aaf(tmp_path: Path):
    """
    True pipeline test:
    - If aaf2 is installed and AAF fixture exists -> run build_canonical CLI
    - Else -> fall back to legacy JSON/CSV fixture
    - Then write FCPXML under reports/integration and emit a comparison report
    """
    reports_dir = Path("reports/integration")
    reports_dir.mkdir(parents=True, exist_ok=True)

    built: dict | None = None
    built_source = None

    if HAS_AAF2 and AAF_PATH.exists():
        out_json = tmp_path / "candidate_from_aaf.canonical.json"
        cmd = ["python", "-m", "src.build_canonical", str(AAF_PATH), "-o", str(out_json)]
        cp = subprocess.run(cmd, capture_output=True, text=True)
        assert cp.returncode == 0, (
            f"build_canonical failed: {cp.returncode}\\nSTDOUT:\\n{cp.stdout}\\nSTDERR:\\n{cp.stderr}"
        )
        assert out_json.exists(), "canonical JSON not produced"
        built = json.loads(out_json.read_text(encoding="utf-8"))
        built_source = "aaf"
    else:
        legacy = _maybe_load_legacy()
        if legacy is None:
            pytest.skip(
                "aaf2 not available or AAF missing, and no legacy JSON/CSV provided; skipping pipeline."
            )
        built = legacy
        built_source = "legacy"

    # Write FCPXML
    fcpxml_path = reports_dir / "candidate_from_aaf.fcpxml"
    write_fcpxml_from_canonical(built, str(fcpxml_path))
    assert fcpxml_path.exists(), f"expected FCPXML at {fcpxml_path}"

    # Emit compare report (uses legacy if available)
    legacy = _maybe_load_legacy()
    compare = _shallow_compare(built, legacy)
    report = {
        "test": "pipeline_aaf",
        "source": built_source,
        "has_aaf": AAF_PATH.exists(),
        "has_aaf2": HAS_AAF2,
        "has_legacy": legacy is not None,
        "aaf": str(AAF_PATH) if AAF_PATH.exists() else None,
        "fcpxml_path": str(fcpxml_path),
        "compare": compare,
    }
    (reports_dir / "candidate_compare.report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
