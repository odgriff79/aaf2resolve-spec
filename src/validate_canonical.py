# @owner: GPT   # CL → GPT → CO
# @version: 1.001
# @status: in_progress
# @spec_compliance: ["docs/data_model_json.md", "docs/collaboration_protocol.md"]
# @handoff_ready: true
# @integration_points: ["validate_canonical_json()", "CLI entrypoint main()"]
# @notes: Clean, lint-safe baseline. JSON Schema + additional validations. Designed to pass pre-commit.

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

try:
    from jsonschema import Draft7Validator, ValidationError  # type: ignore
except Exception as e:  # pragma: no cover
    print(
        "ERROR: jsonschema library required. Install with: pip install jsonschema",
        file=sys.stderr,
    )
    sys.exit(1)


# ----------------------------- Reason Codes -----------------------------


class ReasonCodes:
    """Reason codes for validation failures, mapped to docs/data_model_json.md sections."""

    # Top-level structure
    MISSING_PROJECT = "CANON-REQ-001"
    MISSING_TIMELINE = "CANON-REQ-002"
    EXTRA_TOP_LEVEL_KEYS = "CANON-REQ-003"

    # Project object
    MISSING_PROJECT_NAME = "CANON-REQ-004"
    MISSING_PROJECT_EDIT_RATE = "CANON-REQ-005"
    MISSING_PROJECT_TC_FORMAT = "CANON-REQ-006"
    INVALID_TC_FORMAT = "CANON-REQ-007"
    INVALID_EDIT_RATE = "CANON-REQ-008"

    # Timeline object
    MISSING_TIMELINE_NAME = "CANON-REQ-009"
    MISSING_TIMELINE_START_TC = "CANON-REQ-010"
    MISSING_TIMELINE_EVENTS = "CANON-REQ-011"
    INVALID_START_TC_FRAMES = "CANON-REQ-012"

    # Event objects
    MISSING_EVENT_ID = "CANON-REQ-013"
    MISSING_EVENT_TIMELINE_START = "CANON-REQ-014"
    MISSING_EVENT_LENGTH = "CANON-REQ-015"
    MISSING_EVENT_SOURCE = "CANON-REQ-016"
    MISSING_EVENT_EFFECT = "CANON-REQ-017"
    INVALID_TIMELINE_START = "CANON-REQ-018"
    INVALID_LENGTH_FRAMES = "CANON-REQ-019"
    INVALID_EVENT_ID_FORMAT = "CANON-REQ-020"

    # Source objects
    MISSING_SOURCE_PATH = "CANON-REQ-021"
    MISSING_SOURCE_UMID_CHAIN = "CANON-REQ-022"
    MISSING_SOURCE_TAPE_ID = "CANON-REQ-023"
    MISSING_SOURCE_DISK_LABEL = "CANON-REQ-024"
    MISSING_SOURCE_TC_START = "CANON-REQ-025"
    MISSING_SOURCE_RATE_FPS = "CANON-REQ-026"
    MISSING_SOURCE_DROP = "CANON-REQ-027"
    INVALID_UMID_CHAIN = "CANON-REQ-028"

    # Effect objects
    MISSING_EFFECT_NAME = "CANON-REQ-029"
    MISSING_EFFECT_ON_FILLER = "CANON-REQ-030"
    MISSING_EFFECT_PARAMETERS = "CANON-REQ-031"
    MISSING_EFFECT_KEYFRAMES = "CANON-REQ-032"
    MISSING_EFFECT_EXTERNAL_REFS = "CANON-REQ-033"

    # Keyframe structure
    MISSING_KEYFRAME_TIME = "CANON-REQ-034"
    MISSING_KEYFRAME_VALUE = "CANON-REQ-035"
    INVALID_KEYFRAME_TIME = "CANON-REQ-036"
    KEYFRAME_TIME_ORDER = "CANON-REQ-037"

    # External references
    MISSING_EXTREF_KIND = "CANON-REQ-038"
    MISSING_EXTREF_PATH = "CANON-REQ-039"


# ------------------------------ Data classes ------------------------------


@dataclass
class ValidationErrorReport:
    code: str
    path: str
    message: str
    doc: str


@dataclass
class ValidationReport:
    ok: bool
    errors: List[ValidationErrorReport]
    summary: Dict[str, Any]


# ------------------------------- JSON Schema ------------------------------


def get_canonical_json_schema() -> Dict[str, Any]:
    """Return draft-07 schema for canonical JSON per docs/data_model_json.md."""
    return {
        "$schema": "https://json-schema.org/draft-07/schema#",
        "title": "AAF→Resolve Canonical JSON Schema",
        "type": "object",
        "required": ["project", "timeline"],
        "additionalProperties": False,
        "properties": {
            "project": {
                "type": "object",
                "required": ["name", "edit_rate_fps", "tc_format"],
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string"},
                    "edit_rate_fps": {"type": "number", "exclusiveMinimum": 0},
                    "tc_format": {"type": "string", "enum": ["DF", "NDF"]},
                },
            },
            "timeline": {
                "type": "object",
                "required": ["name", "start_tc_frames", "events"],
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string"},
                    "start_tc_frames": {"type": "integer", "minimum": 0},
                    "events": {"type": "array", "items": {"$ref": "#/definitions/event"}},
                },
            },
        },
        "definitions": {
            "event": {
                "type": "object",
                "required": [
                    "id",
                    "timeline_start_frames",
                    "length_frames",
                    "source",
                    "effect",
                ],
                "additionalProperties": False,
                "properties": {
                    "id": {"type": "string", "pattern": r"^ev_\d{4}$"},
                    "timeline_start_frames": {"type": "integer", "minimum": 0},
                    "length_frames": {"type": "integer", "minimum": 1},
                    "source": {"oneOf": [{"type": "null"}, {"$ref": "#/definitions/source"}]},
                    "effect": {"$ref": "#/definitions/effect"},
                },
            },
            "source": {
                "type": "object",
                "required": [
                    "path",
                    "umid_chain",
                    "tape_id",
                    "disk_label",
                    "src_tc_start_frames",
                    "src_rate_fps",
                    "src_drop",
                ],
                "additionalProperties": False,
                "properties": {
                    "path": {"oneOf": [{"type": "string"}, {"type": "null"}]},
                    "umid_chain": {"type": "array", "items": {"type": "string"}},
                    "tape_id": {"oneOf": [{"type": "string"}, {"type": "null"}]},
                    "disk_label": {"oneOf": [{"type": "string"}, {"type": "null"}]},
                    "src_tc_start_frames": {
                        "oneOf": [{"type": "integer", "minimum": 0}, {"type": "null"}]
                    },
                    "src_rate_fps": {"type": "number", "exclusiveMinimum": 0},
                    "src_drop": {"type": "boolean"},
                },
            },
            "effect": {
                "type": "object",
                "required": ["name", "on_filler", "parameters", "keyframes", "external_refs"],
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string"},
                    "on_filler": {"type": "boolean"},
                    "parameters": {
                        "type": "object",
                        "patternProperties": {
                            ".*": {"oneOf": [{"type": "number"}, {"type": "string"}, {"type": "null"}]}
                        },
                    },
                    "keyframes": {
                        "type": "object",
                        "patternProperties": {
                            ".*": {"type": "array", "items": {"$ref": "#/definitions/keyframe"}}
                        },
                    },
                    "external_refs": {
                        "type": "array",
                        "items": {"$ref": "#/definitions/external_ref"},
                    },
                },
            },
            "keyframe": {
                "type": "object",
                "required": ["t", "v"],
                "additionalProperties": False,
                "properties": {
                    "t": {"type": "number", "minimum": 0},
                    "v": {"oneOf": [{"type": "number"}, {"type": "string"}]},
                },
            },
            "external_ref": {
                "type": "object",
                "required": ["kind", "path"],
                "additionalProperties": False,
                "properties": {
                    "kind": {"type": "string", "enum": ["image", "matte", "unknown"]},
                    "path": {"type": "string"},
                },
            },
        },
    }


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
        elif "source" in path:
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


def _run_additional_validations(data: Dict[str, Any]) -> List[ValidationErrorReport]:
    """Checks not expressible in JSON Schema."""
    errors: List[ValidationErrorReport] = []

    # Keyframe time ordering
    try:
        events = data.get("timeline", {}).get("events", [])
        for ei, ev in enumerate(events):
            effect = ev.get("effect", {})
            kfs = effect.get("keyframes", {})
            for pname, arr in kfs.items():
                if isinstance(arr, list) and len(arr) > 1:
                    times = [k.get("t") for k in arr if isinstance(k, dict) and "t" in k]
                    if times != sorted(times):
                        errors.append(
                            ValidationErrorReport(
                                code=ReasonCodes.KEYFRAME_TIME_ORDER,
                                path=f"$.timeline.events[{ei}].effect.keyframes.{pname}",
                                message=f"Keyframes not ordered by time: {times}",
                                doc="docs/data_model_json.md#parameter--keyframe-capture",
                            )
                        )
    except Exception as e:  # pragma: no cover
        errors.append(
            ValidationErrorReport(
                code="CANON-INTERNAL-ERROR",
                path="$",
                message=f"Internal validation error: {e}",
                doc="docs/data_model_json.md",
            )
        )

    # UMID chain sanity: non-empty strings
    events = data.get("timeline", {}).get("events", [])
    for ei, ev in enumerate(events):
        src = ev.get("source")
        if src and isinstance(src, dict):
            chain = src.get("umid_chain", [])
            if isinstance(chain, list):
                for ui, u in enumerate(chain):
                    if not isinstance(u, str) or not u.strip():
                        errors.append(
                            ValidationErrorReport(
                                code=ReasonCodes.INVALID_UMID_CHAIN,
                                path=f"$.timeline.events[{ei}].source.umid_chain[{ui}]",
                                message=f"UMID must be non-empty string, found: {repr(u)}",
                                doc="docs/data_model_json.md#identifiers",
                            )
                        )

    return errors


def validate_canonical_json(data: Dict[str, Any], verbose: bool = False) -> ValidationReport:
    """Validate canonical JSON against schema + custom rules."""
    schema = get_canonical_json_schema()
    validator = Draft7Validator(schema)

    errors: List[ValidationErrorReport] = []
    checked = 0

    for e in validator.iter_errors(data):
        checked += 1
        errors.append(map_validation_error_to_reason_code(e))
        if verbose:
            print(f"❌ {errors[-1].code}: {errors[-1].message} at {errors[-1].path}", file=sys.stderr)

    extra = _run_additional_validations(data)
    errors.extend(extra)
    checked += len(extra)

    summary = {"checked": checked, "failed": len(errors), "reason_codes": [er.code for er in errors]}
    if verbose:
        print(("✅ Passed" if not errors else f"❌ Failed with {len(errors)} errors"), file=sys.stderr)

    return ValidationReport(ok=not errors, errors=errors, summary=summary)


# ------------------------------ CLI utilities ------------------------------


def load_and_validate_json_file(file_path: str, verbose: bool = False) -> ValidationReport:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return ValidationReport(
            ok=False,
            errors=[
                ValidationErrorReport(
                    code="CANON-FILE-ERROR", path="$", message=f"File not found: {file_path}", doc="docs/data_model_json.md"
                )
            ],
            summary={"checked": 0, "failed": 1, "reason_codes": ["CANON-FILE-ERROR"]},
        )
    except json.JSONDecodeError as e:
        return ValidationReport(
            ok=False,
            errors=[
                ValidationErrorReport(
                    code="CANON-PARSE-ERROR", path=f"line {e.lineno}", message=f"Invalid JSON: {e.msg}", doc="docs/data_model_json.md"
                )
            ],
            summary={"checked": 0, "failed": 1, "reason_codes": ["CANON-PARSE-ERROR"]},
        )
    return validate_canonical_json(data, verbose=verbose)


def write_validation_report(report: ValidationReport, output_path: Optional[str] = None) -> None:
    payload = {
        "ok": report.ok,
        "errors": [{"code": e.code, "path": e.path, "message": e.message, "doc": e.doc} for e in report.errors],
        "summary": report.summary,
    }
    s = json.dumps(payload, indent=2, ensure_ascii=False)
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(s)
    else:
        print(s)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate canonical JSON against docs/data_model_json.md schema")
    parser.add_argument("json_file", help="Path to canonical JSON file to validate")
    parser.add_argument("--report", "-r", help="Write JSON validation report to file (default: stdout)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging to stderr")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress stdout")
    args = parser.parse_args()

    if args.verbose:
        print(f"🚀 Validating {args.json_file}", file=sys.stderr)

    report = load_and_validate_json_file(args.json_file, verbose=args.verbose and not args.quiet)

    if not args.quiet:
        write_validation_report(report, args.report)
        if not report.ok and not args.report:
            print(f"\n❌ Validation failed with {len(report.errors)} errors", file=sys.stderr)

    if report.ok:
        return 0
    if any(c.code.startswith("CANON-PARSE") or c.code.startswith("CANON-FILE") for c in report.errors):
        return 2
    return 1


if __name__ == "__main__":
    sys.exit(main())
