from pathlib import Path

from src.write_fcpxml import write_fcpxml_from_canonical


def test_pipeline_minimal(tmp_path):
    """
    Full pipeline test (minimal):
    - Build a minimal canonical dict inline
    - Write FCPXML to reports/integration/minimal_pipeline.fcpxml
    - Assert file exists (shape validated by other tests)
    """
    canonical = {
        "timeline": {
            "name": "Test Timeline",
            "rate": 25,
            "start": "10:00:00:00",
            "tracks": [
                {
                    "clips": [
                        {
                            "name": "Test Clip",
                            "path": "/tmp/test.mov",
                            "start": "10:00:00:00",
                            "end": "10:00:01:00",
                        }
                    ]
                }
            ],
        }
    }

    reports_dir = Path("reports/integration")
    reports_dir.mkdir(parents=True, exist_ok=True)
    out_path = reports_dir / "minimal_pipeline.fcpxml"

    write_fcpxml_from_canonical(canonical, str(out_path))
    assert out_path.exists(), f"Expected FCPXML at {out_path}"
