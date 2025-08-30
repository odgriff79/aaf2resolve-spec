#!/usr/bin/env python3
import re

#!/usr/bin/env python3

"""
Validation utilities for the canonical AAF2Resolve JSON schema.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Any

try:
    from jsonschema.validators import Draft7Validator
except ImportError:
    print("jsonschema is required for validation.", file=sys.stderr)
    raise


@dataclass
class ValidationErrorReport:
    code: str
    path: list[str]
    message: str
    doc: str | None = None


@dataclass
class ValidationReport:
    ok: bool
    errors: list["ValidationErrorReport"]
    summary: dict[str, Any]


def get_canonical_json_schema() -> dict[str, Any]:
    """
    Return JSON Schema (draft-07) for canonical JSON per docs/data_model_json.md.
    """
    # ... (your schema definition here, unchanged for brevity) ...
    schema = {
        "type": "object",
        "properties": {
            "field1": {"type": "string"},
            "field2": {
                "type": "integer",
                "description": ("Original full source clip length in frames " "(from descriptor)"),
            },
            "extras": {
                "type": "object",
                "additionalProperties": True,
                "description": ("Vendor/tool-specific extras; non-canonical " "and safe to ignore"),
            },
        },
        "required": ["field1", "field2"],
        "additionalProperties": False,
    }
    return schema


def validate_event_ids(data: dict[str, Any]) -> list[ValidationErrorReport]:
    """Validate event IDs follow the pattern ev_NNNN (see docs/data_model_json.md)."""
    errors: list[ValidationErrorReport] = []

    timeline = data.get("timeline")
    if not isinstance(timeline, dict):
        return errors

    events = timeline.get("events")
    if not isinstance(events, list):
        return errors

    for i, event in enumerate(events):
        if not isinstance(event, dict):
            continue

        event_id = event.get("id")
        if not isinstance(event_id, str):
            errors.append(
                ValidationErrorReport(
                    code="CANON-REQ-020",
                    path=["timeline", "events", str(i), "id"],
                    message="Event ID must be a string",
                    doc="docs/data_model_json.md#identifiers",
                )
            )
            continue

        # Accept ev_ followed by exactly 4 digits
        if re.fullmatch(r"ev_\d{4}", event_id) is None:
            errors.append(
                ValidationErrorReport(
                    code="CANON-REQ-020",
                    path=["timeline", "events", str(i), "id"],
                    message=f"Event ID {event_id} does not match required pattern ev_NNNN",
                    doc="docs/data_model_json.md#identifiers",
                )
            )

    return errors


def _run_additional_validations(data: dict[str, Any]) -> list[ValidationErrorReport]:
    """Checks not expressible in JSON Schema."""
    errors: list[ValidationErrorReport] = []

    # Keyframe time ordering: each parameter's keyframe times must be non-decreasing.
    kfs = data.get("keyframes")
    if isinstance(kfs, dict):
        for pname, arr in kfs.items():
            if isinstance(arr, list) and len(arr) > 1:
                times: list[float] = [
                    float(k["t"])
                    for k in arr
                    if isinstance(k, dict) and isinstance(k.get("t"), int | float)
                ]
                for earlier, later in zip(times, times[1:], strict=False):
                    if earlier > later:
                        errors.append(
                            ValidationErrorReport(
                                code="CANON-KF-ORDER",
                                path=["keyframes", pname],
                                message="Keyframe times must be non-decreasing",
                                doc="docs/data_model_json.md#keyframes",
                            )
                        )
                        break

    return errors
    errors.extend(validate_event_ids(data))


def validate_canonical_json(data: dict[str, Any], verbose: bool = False) -> ValidationReport:
    """Validate canonical JSON against schema + custom rules."""
    schema = get_canonical_json_schema()
    validator = Draft7Validator(schema)

    errors: list[ValidationErrorReport] = []
    checked = 0

    for err in validator.iter_errors(data):
        checked += 1
        errors.append(
            ValidationErrorReport(
                code="CANON-SCHEMA",
                path=list(err.absolute_path),
                message=err.message,
            )
        )

    # Run custom checks
    extra = _run_additional_validations(data)
    errors.extend(extra)
    checked += len(extra)

    summary = {
        "checked": checked,
        "failed": len(errors),
        "reason_codes": [er.code for er in errors],
    }
    if verbose:
        result_msg = "✅ Passed" if not errors else f"❌ Failed with {len(errors)} errors"
        print(
            result_msg,
            file=sys.stderr,
        )

    return ValidationReport(ok=not errors, errors=errors, summary=summary)


def load_and_validate_json_file(file_path: str, verbose: bool = False) -> ValidationReport:
    try:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"File not found: {file_path}", file=sys.stderr)
        raise
    return validate_canonical_json(data, verbose=verbose)


def write_validation_report(report: ValidationReport, output_path: str | None = None) -> None:
    payload = {
        "ok": report.ok,
        "errors": [
            {
                "code": e.code,
                "path": e.path,
                "message": e.message,
                "doc": e.doc,
            }
            for e in report.errors
        ],
        "summary": report.summary,
    }
    out = json.dumps(payload, indent=2)
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(out)
    else:
        print(out)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate canonical JSON file against schema and custom rules"
    )
    parser.add_argument(
        "json_file",
        help="Path to canonical JSON file to validate",
    )
    parser.add_argument(
        "--report",
        "-r",
        help="Write JSON validation report to file (default: stdout)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose logging to stderr",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress stdout",
    )

    args = parser.parse_args()
    report = load_and_validate_json_file(args.json_file, verbose=args.verbose)
    if not args.quiet:
        write_validation_report(report, output_path=args.report)

    if report.ok:
        sys.exit(0)
    if any(
        c.code.startswith("CANON-PARSE") or c.code.startswith("CANON-FILE") for c in report.errors
    ):
        sys.exit(2)
    sys.exit(1)
