#!/usr/bin/env python3

"""
Validation utilities for the canonical AAF2Resolve JSON schema.
"""

from __future__ import annotations
import sys
import json
from dataclasses import dataclass
from typing import Any

try:
    import jsonschema
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

class ValidationReport:
    ok: bool
    errors: list[ValidationErrorReport]
    summary: dict[str, Any]

<<<<<<< HEAD
=======

# ------------------------------- JSON Schema ------------------------------


>>>>>>> 92a31e6 (Fix all lint/style issues: modernize types, wrap long lines, and auto-format)
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
                "description": (
                    "Original full source clip length in frames "
                    "(from descriptor)"
                ),
            },
            "extras": {
                "type": "object",
                "additionalProperties": True,
                "description": (
                    "Vendor/tool-specific extras; non-canonical "
                    "and safe to ignore"
                ),
            },
        },
        "required": ["field1", "field2"],
        "additionalProperties": False,
    }
    return schema

<<<<<<< HEAD
def _run_additional_validations(
    data: dict[str, Any],
) -> list[ValidationErrorReport]:
    """Checks not expressible in JSON Schema."""
    errors: list[ValidationErrorReport] = []

    # Example: keyframe time ordering
    if "keyframes" in data:
        kfs = data["keyframes"]
        for pname, arr in kfs.items():
            if isinstance(arr, list) and len(arr) > 1:
                times: list[float] = [
                    k.get("t") for k in arr if isinstance(k, dict) and "t" in k
                ]  # type: ignore
                for earlier, later in zip(times, times[1:]):
                    if earlier > later:
=======

# ------------------------------ Core validation ------------------------------


def map_validation_error_to_reason_code(error: ValidationError) -> ValidationErrorReport:
    """Convert jsonschema error to our reason-code structure."""
    path = list(error.absolute_path)
    path_str = f"$.{'.'.join(str(p) for p in path)}" if path else "$"

    if error.validator == "required":
        missing = error.message.split("'")[1]
        if not path:
            code = (
                ReasonCodes.MISSING_PROJECT
                if missing == "project"
                else ReasonCodes.MISSING_TIMELINE
                if missing == "timeline"
                else ReasonCodes.EXTRA_TOP_LEVEL_KEYS
            )
        elif path[0] == "project":
            code = {
                "name": ReasonCodes.MISSING_PROJECT_NAME,
                "edit_rate_fps": ReasonCodes.MISSING_PROJECT_EDIT_RATE,
                "tc_format": ReasonCodes.MISSING_PROJECT_TC_FORMAT,
            }.get(missing, ReasonCodes.EXTRA_TOP_LEVEL_KEYS)
        elif path[0] == "timeline":
            code = {
                "name": ReasonCodes.MISSING_TIMELINE_NAME,
                "start_tc_frames": ReasonCodes.MISSING_TIMELINE_START_TC,
                "events": ReasonCodes.MISSING_TIMELINE_EVENTS,
            }.get(missing, ReasonCodes.EXTRA_TOP_LEVEL_KEYS)
        elif "events" in path:
            code = {
                "id": ReasonCodes.MISSING_EVENT_ID,
                "timeline_start_frames": ReasonCodes.MISSING_EVENT_TIMELINE_START,
                "length_frames": ReasonCodes.MISSING_EVENT_LENGTH,
                "source": ReasonCodes.MISSING_EVENT_SOURCE,
                "effect": ReasonCodes.MISSING_EVENT_EFFECT,
            }.get(missing, ReasonCodes.EXTRA_TOP_LEVEL_KEYS)
        elif "source" in path and "original" in path:
            # Map missing fields inside source.original
            code = {
                "path": ReasonCodes.MISSING_SOURCE_PATH,
                "umid_chain": ReasonCodes.MISSING_SOURCE_UMID_CHAIN,
                "tape_id": ReasonCodes.MISSING_SOURCE_TAPE_ID,
                "disk_label": ReasonCodes.MISSING_SOURCE_DISK_LABEL,
                "src_tc_start_frames": ReasonCodes.MISSING_SOURCE_TC_START,
                "src_rate_fps": ReasonCodes.MISSING_SOURCE_RATE_FPS,
                "src_drop": ReasonCodes.MISSING_SOURCE_DROP,
            }.get(missing, ReasonCodes.EXTRA_TOP_LEVEL_KEYS)
        elif "effect" in path:
            code = {
                "name": ReasonCodes.MISSING_EFFECT_NAME,
                "on_filler": ReasonCodes.MISSING_EFFECT_ON_FILLER,
                "parameters": ReasonCodes.MISSING_EFFECT_PARAMETERS,
                "keyframes": ReasonCodes.MISSING_EFFECT_KEYFRAMES,
                "external_refs": ReasonCodes.MISSING_EFFECT_EXTERNAL_REFS,
            }.get(missing, ReasonCodes.EXTRA_TOP_LEVEL_KEYS)
        else:
            code = ReasonCodes.EXTRA_TOP_LEVEL_KEYS
    elif error.validator == "enum" and "tc_format" in path_str:
        code = ReasonCodes.INVALID_TC_FORMAT
    elif error.validator in {"minimum", "exclusiveMinimum"}:
        if "edit_rate_fps" in path_str:
            code = ReasonCodes.INVALID_EDIT_RATE
        elif "start_tc_frames" in path_str:
            code = ReasonCodes.INVALID_START_TC_FRAMES
        elif "timeline_start_frames" in path_str:
            code = ReasonCodes.INVALID_TIMELINE_START
        elif "length_frames" in path_str:
            code = ReasonCodes.INVALID_LENGTH_FRAMES
        elif "keyframes" in path_str and ".t" in path_str:
            code = ReasonCodes.INVALID_KEYFRAME_TIME
        else:
            code = ReasonCodes.EXTRA_TOP_LEVEL_KEYS
    elif error.validator == "pattern" and ".id" in path_str:
        code = ReasonCodes.INVALID_EVENT_ID_FORMAT
    else:
        code = ReasonCodes.EXTRA_TOP_LEVEL_KEYS

    return ValidationErrorReport(
        code=code, path=path_str, message=error.message, doc="docs/data_model_json.md"
    )


def _run_additional_validations(data: dict[str, Any]) -> list[ValidationErrorReport]:
    """Checks not expressible in JSON Schema."""
    errors: list[ValidationErrorReport] = []

    # Keyframe time ordering
    try:
        events = data.get("timeline", {}).get("events", [])
        for ei, ev in enumerate(events):
            effect = ev.get("effect", {}) or {}
            kfs = effect.get("keyframes", {}) or {}
            for pname, arr in kfs.items():
                if isinstance(arr, list) and len(arr) > 1:
                    times: list[float] = [
                        k.get("t") for k in arr if isinstance(k, dict) and "t" in k
                    ]  # type: ignore
                    if times != sorted(times):
>>>>>>> 92a31e6 (Fix all lint/style issues: modernize types, wrap long lines, and auto-format)
                        errors.append(
                            ValidationErrorReport(
                                code="ORDER",
                                path=["keyframes", pname],
                                message="Keyframes not in time order.",
                            )
                        )
    return errors

<<<<<<< HEAD
def validate_canonical_json(
    data: dict[str, Any], verbose: bool = False
) -> ValidationReport:
=======

def validate_canonical_json(data: dict[str, Any], verbose: bool = False) -> ValidationReport:
>>>>>>> 92a31e6 (Fix all lint/style issues: modernize types, wrap long lines, and auto-format)
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
        result_msg = (
            "✅ Passed"
            if not errors
            else f"❌ Failed with {len(errors)} errors"
        )
        print(
            result_msg,
            file=sys.stderr,
        )

    return ValidationReport(ok=not errors, errors=errors, summary=summary)

def load_and_validate_json_file(
    file_path: str, verbose: bool = False
) -> ValidationReport:
    try:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"File not found: {file_path}", file=sys.stderr)
        raise
    return validate_canonical_json(data, verbose=verbose)

<<<<<<< HEAD
def write_validation_report(
    report: ValidationReport, output_path: str | None = None
) -> None:
=======

def write_validation_report(report: ValidationReport, output_path: str | None = None) -> None:
>>>>>>> 92a31e6 (Fix all lint/style issues: modernize types, wrap long lines, and auto-format)
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
        c.code.startswith("CANON-PARSE") or c.code.startswith("CANON-FILE")
        for c in report.errors
    ):
        sys.exit(2)
    sys.exit(1)
