from __future__ import annotations

import glob
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from src.write_fcpxml import write_fcpxml_from_canonical  # type: ignore


def _fcpxml_shape_summary(fcpxml_path: Path) -> dict:
    """
    Conservative FCPXML 1.13 shape check.
    Verifies root/version and presence of library/event/project/sequence/spine.
    Returns a summary dict with booleans and simple counts.
    """
    fcpxml_path = Path(fcpxml_path)
    tree = ET.parse(fcpxml_path)
    root = tree.getroot()

    # Basic root/version checks
    root_ok = (root.tag == "fcpxml")
    version = root.attrib.get("version", "")
    version_ok = version.startswith("1.13")

    # Structural presence
    library = root.find("library")
    event = library.find("event") if library is not None else None
    project = event.find("project") if event is not None else None
    sequence = project.find("sequence") if project is not None else None
    spine = sequence.find("spine") if sequence is not None else None

    has_library = library is not None
    has_event = event is not None
    has_project = project is not None
    has_sequence = sequence is not None
    has_spine = spine is not None

    # Simple counts
    events_count = len(root.findall(".//event"))
    projects_count = len(root.findall(".//project"))
    spines_count = len(root.findall(".//spine"))
    items_in_spine = len(spine.findall("./*")) if spine is not None else 0

    ok = all([root_ok, version_ok, has_library, has_event, has_project, has_sequence, has_spine])

    return {
        "ok": ok,
        "version": version,
        "root_ok": root_ok,
        "version_ok": version_ok,
        "has_library": has_library,
        "has_event": has_event,
        "has_project": has_project,
        "has_sequence": has_sequence,
        "has_spine": has_spine,
        "counts": {
            "events": events_count,
            "projects": projects_count,
            "spines": spines_count,
            "items_in_spine": items_in_spine,
        },
    }



ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "tests" / "samples"
REPORTS = ROOT / "reports" / "integration"



def sample_json_files():
    return sorted(SAMPLES.glob("*.json")) if SAMPLES.exists() else []


@pytest.mark.parametrize("sample_path", sample_json_files())
def test_canonical_to_fcpxml_parses_and_writes_artifact(sample_path: Path):
    REPORTS.mkdir(parents=True, exist_ok=True)

    data = json.loads(sample_path.read_text(encoding="utf-8"))
    out_xml = REPORTS / f"{sample_path.stem}.fcpxml"

    # writer requires out_path; some impls also return text
    maybe_text = write_fcpxml_from_canonical(data, out_xml)

    fcpxml_text = (
        maybe_text if isinstance(maybe_text, str) and maybe_text.strip()
        else out_xml.read_text(encoding="utf-8")
    )
    assert isinstance(fcpxml_text, str) and len(fcpxml_text) > 0

    # well-formed XML check
    ET.fromstring(fcpxml_text)

    report = {
        "sample": str(sample_path.relative_to(ROOT)),
        "fcpxml": str(out_xml.relative_to(ROOT)),
        "bytes": len(fcpxml_text.encode("utf-8")),
        "status": "ok",
    }
    (REPORTS / f"{sample_path.stem}.report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )

def test_fcpxml_shape_report(tmp_path, request):
    """
    Post-check: parse the FCPXML produced in earlier integration tests,
    validate its shape, and write a JSON report to reports/integration/.
    """

    # Find the most recent FCPXML file written during tests
    candidates = sorted(glob.glob("reports/integration/*.fcpxml"))
    assert candidates, "No FCPXML files found in reports/integration/"
    fcpxml_path = Path(candidates[-1])

    summary = _fcpxml_shape_summary(fcpxml_path)
    reports_dir = Path("reports/integration")
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_name = f"{request.node.name}.report.json"
    report_path = reports_dir / report_name
    report_payload = {
        "test": request.node.name,
        "fcpxml_path": str(fcpxml_path),
        "summary": summary,
    }
    report_path.write_text(json.dumps(report_payload, indent=2), encoding="utf-8")

    assert summary["ok"], f"FCPXML shape check failed: {json.dumps(summary, indent=2)}"

@pytest.mark.parametrize("fcpxml_path", sorted(glob.glob("reports/integration/*.fcpxml")))
def test_fcpxml_shape_report_all(fcpxml_path):
    """
    Generate a shape report for each FCPXML found in reports/integration/.
    Writes <stem>.report.json beside the FCPXML.
    """

    fcpxml_path = Path(fcpxml_path)
    summary = _fcpxml_shape_summary(fcpxml_path)

    report_path = fcpxml_path.with_suffix(".report.json")
    payload = {
        "test": "fcpxml_shape_report",
        "fcpxml_path": str(fcpxml_path),
        "summary": summary,
    }
    report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    assert summary["ok"], f"FCPXML shape check failed for {fcpxml_path}: " + json.dumps(summary, indent=2)