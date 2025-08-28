#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_canonical.py — Canonical JSON Schema Validator

Purpose:
  Validate any canonical JSON against the specification in docs/data_model_json.md.
  Establish "schema-as-law" principle with rich error reporting and reason codes.

Authoritative spec:
  - docs/data_model_json.md (single source of truth)

Core principle:
  • Required keys must always be present (even if null)
  • Unknown/unavailable values = null (never omit keys)
  • Path fidelity preserved (no normalization validation)
  • Rich error reporting with reason codes and JSON paths
"""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass

try:
    import jsonschema
    from jsonschema import Draft7Validator, ValidationError
except ImportError:
    print("ERROR: jsonschema library required. Install with: pip install jsonschema", file=sys.stderr)
    sys.exit(1)


# ========================= REASON CODES =========================

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


# ========================= SCHEMA DEFINITION =========================

def _run_additional_validations(data: Dict[str, Any]) -> List[ValidationErrorReport]:
    """
    Run additional validations not covered by JSON Schema.
    
    These include:
    - Keyframe time ordering validation
    - UMID chain content validation
    - Custom business rule checks
    """
    errors = []
    
    try:
        # Validate keyframe time ordering
        if "timeline" in data and "events" in data["timeline"]:
            for event_idx, event in enumerate(data["timeline"]["events"]):
                if "effect" in event and "keyframes" in event["effect"]:
                    for param_name, keyframe_list in event["effect"]["keyframes"].items():
                        if isinstance(keyframe_list, list) and len(keyframe_list) > 1:
                            # Check if keyframes are ordered by time
                            times = []
                            for kf_idx, keyframe in enumerate(keyframe_list):
                                if isinstance(keyframe, dict) and "t" in keyframe:
                                    times.append(keyframe["t"])
                            
                            if times != sorted(times):
                                errors.append(ValidationErrorReport(
                                    code=ReasonCodes.KEYFRAME_TIME_ORDER,
                                    path=f"$.timeline.events[{event_idx}].effect.keyframes.{param_name}",
                                    message=f"Keyframes must be ordered by time (t), found: {times}",
                                    doc="docs/data_model_json.md#parameter--keyframe-capture"
                                ))
        
        # Validate UMID chain contains only non-empty strings
        if "timeline" in data and "events" in data["timeline"]:
            for event_idx, event in enumerate(data["timeline"]["events"]):
                if "source" in event and event["source"] is not None:
                    if "umid_chain" in event["source"]:
                        umid_chain = event["source"]["umid_chain"]
                        if isinstance(umid_chain, list):
                            for umid_idx, umid in enumerate(umid_chain):
                                if not isinstance(umid, str) or not umid.strip():
                                    errors.append(ValidationErrorReport(
                                        code=ReasonCodes.INVALID_UMID_CHAIN,
                                        path=f"$.timeline.events[{event_idx}].source.umid_chain[{umid_idx}]",
                                        message=f"UMID chain must contain only non-empty strings, found: {repr(umid)}",
                                        doc="docs/data_model_json.md#identifiers"
                                    ))
                                    
    except Exception as e:
        # Don't let additional validation errors crash the main validation
        errors.append(ValidationErrorReport(
            code="CANON-INTERNAL-ERROR",
            path="$",
            message=f"Internal validation error: {str(e)}",
            doc="docs/data_model_json.md"
        ))
    
    return errors


def load_and_validate_json_file(file_path: str, verbose: bool = False) -> ValidationReport:
    """
    Load JSON file and validate it against canonical schema.
    
    Args:
        file_path: Path to JSON file to validate
        verbose: Include debug logging
        
    Returns:
        ValidationReport (ok=False if file loading fails)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if verbose:
            print(f"\U0001F4C1 Loaded JSON from {file_path}", file=sys.stderr)
            
        return validate_canonical_json(data, verbose=verbose)
        
    except json.JSONDecodeError as e:
        return ValidationReport(
            ok=False,
            errors=[ValidationErrorReport(
                code="CANON-PARSE-ERROR",
                path=f"line {e.lineno}",
                message=f"Invalid JSON: {e.msg}",
                doc="docs/data_model_json.md"
            )],
            summary={"checked": 0, "failed": 1, "reason_codes": ["CANON-PARSE-ERROR"]}
        )
    except FileNotFoundError:
        return ValidationReport(
            ok=False,
            errors=[ValidationErrorReport(
                code="CANON-FILE-ERROR",
                path="$",
                message=f"File not found: {file_path}",
                doc="docs/data_model_json.md"
            )],
            summary={"checked": 0, "failed": 1, "reason_codes": ["CANON-FILE-ERROR"]}
        )
    except Exception as e:
        return ValidationReport(
            ok=False,
            errors=[ValidationErrorReport(
                code="CANON-INTERNAL-ERROR", 
                path="$",
                message=f"Internal error: {str(e)}",
                doc="docs/data_model_json.md"
            )],
            summary={"checked": 0, "failed": 1, "reason_codes": ["CANON-INTERNAL-ERROR"]}
        )


def write_validation_report(report: ValidationReport, output_path: Optional[str] = None) -> None:
    """
    Write validation report to JSON file or stdout.
    
    Args:
        report: ValidationReport to serialize
        output_path: Output file path, or None for stdout
    """
    # Convert report to JSON-serializable format
    report_dict = {
        "ok": report.ok,
        "errors": [
            {
                "code": error.code,
                "path": error.path, 
                "message": error.message,
                "doc": error.doc
            }
            for error in report.errors
        ],
        "summary": report.summary
    }
    
    report_json = json.dumps(report_dict, indent=2, ensure_ascii=False)
    
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_json)
    else:
        print(report_json)


# ========================= CLI INTERFACE =========================

def main() -> int:
    """
    CLI entrypoint for canonical JSON validation.
    
    Usage:
        python -m src.validate_canonical path/to/canonical.json
        python -m src.validate_canonical --help
        
    Returns:
        0 if validation passes, 1 if validation fails, 2 for other errors
    """
    parser = argparse.ArgumentParser(
        description="Validate canonical JSON against docs/data_model_json.md schema",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.validate_canonical canonical.json
  python -m src.validate_canonical canonical.json --report reports/validation.json
  python -m src.validate_canonical canonical.json --verbose
  
Exit codes:
  0 = validation passed
  1 = validation failed  
  2 = file/parse error
        """
    )
    
    parser.add_argument(
        "json_file",
        help="Path to canonical JSON file to validate"
    )
    
    parser.add_argument(
        "--report", "-r",
        help="Write JSON validation report to file (default: stdout)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging to stderr"
    )
    
    parser.add_argument(
        "--quiet", "-q", 
        action="store_true",
        help="Suppress all output except errors"
    )
    
    args = parser.parse_args()
    
    # Validate file
    if args.verbose:
        print(f"\U0001F680 Starting validation of {args.json_file}", file=sys.stderr)
    
    report = load_and_validate_json_file(args.json_file, verbose=args.verbose and not args.quiet)
    
    # Write report
    if not args.quiet:
        write_validation_report(report, args.report)
        
        if not report.ok and not args.report:
            # Also print human-readable summary to stderr when failing
            print(f"\n❌ Validation failed with {len(report.errors)} errors:", file=sys.stderr)
            for error in report.errors[:5]:  # Show first 5 errors
                print(f"  • {error.code}: {error.message}", file=sys.stderr)
            if len(report.errors) > 5:
                print(f"  ... and {len(report.errors) - 5} more errors", file=sys.stderr)
    
    # Determine exit code
    if report.ok:
        if not args.quiet:
            print(f"✅ Validation passed ({report.summary['checked']} checks)", file=sys.stderr)
        return 0
    elif any(error.code.startswith("CANON-PARSE") or error.code.startswith("CANON-FILE") 
             for error in report.errors):
        return 2  # File/parse error
    else:
        return 1  # Validation error


# ========================= TESTING INTERFACE =========================

def create_minimal_valid_example() -> Dict[str, Any]:
    """
    Create minimal valid canonical JSON for testing.
    
    Based on the minimal example in docs/data_model_json.md.
    """
    return {
        "project": {
            "name": "MyTimeline",
            "edit_rate_fps": 25.0,
            "tc_format": "NDF"
        },
        "timeline": {
            "name": "MyTimeline.Exported.01",
            "start_tc_frames": 3600,
            "events": [
                {
                    "id": "ev_0001",
                    "timeline_start_frames": 0,
                    "length_frames": 100,
                    "source": {
                        "path": "file:///Volumes/Media/clip01.mov",
                        "umid_chain": ["{UMID-A}", "{UMID-B}"],
                        "tape_id": None,
                        "disk_label": "DISK01",
                        "src_tc_start_frames": 90000,
                        "src_rate_fps": 25.0,
                        "src_drop": False
                    },
                    "effect": {
                        "name": "(none)",
                        "on_filler": False,
                        "parameters": {},
                        "keyframes": {},
                        "external_refs": []
                    }
                }
            ]
        }
    }


if __name__ == "__main__":
    sys.exit(main())