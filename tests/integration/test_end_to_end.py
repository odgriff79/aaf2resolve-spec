from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "tests" / "samples"
REPORTS = ROOT / "reports" / "integration"

from src.write_fcpxml import write_fcpxml_from_canonical  # type: ignore


def sample_json_files():
    return sorted(SAMPLES.glob("*.json")) if SAMPLES.exists() else []


@pytest.mark.parametrize("sample_path", sample_json_files())
def test_canonical_to_fcpxml_parses_and_writes_artifact(sample_path: Path):
    REPORTS.mkdir(parents=True, exist_ok=True)

    data = json.loads(sample_path.read_text(encoding="utf-8"))
    out_xml = REPORTS / f"{sample_path.stem}.fcpxml"

    # call writer with required out_path
    maybe_text = write_fcpxml_from_canonical(data, out_xml)

    # normalize to text for parsing
    fcpxml_text = (
        maybe_text if isinstance(maybe_text, str) and maybe_text.strip()
        else out_xml.read_text(encoding="utf-8")
    )
    assert isinstance(fcpxml_text, str) and len(fcpxml_text) > 0

    # XML must be well-formed
    ET.fromstring(fcpxml_text)

    # write a small JSON report next to the artifact
    report = {
        "sample": str(sample_path.relative_to(ROOT)),
        "fcpxml": str(out_xml.relative_to(ROOT)),
        "bytes": len(fcpxml_text.encode("utf-8")),
        "status": "ok",
    }
    (REPORTS / f"{sample_path.stem}.report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
