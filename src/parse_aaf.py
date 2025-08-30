#!/usr/bin/env python3
"""
parse_aaf.py — SPEC-FIRST CLI WRAPPER (no business logic)

Purpose:
  Thin CLI that delegates to build_canonical_from_aaf() and prints/writes the
  **canonical JSON** defined in docs/data_model_json.md.

This file MUST NOT implement traversal or extraction logic.
All behavior is defined by:
  - docs/inspector_rule_pack.md           (timeline traversal, UMID resolution, effects)
  - docs/data_model_json.md               (canonical JSON; required keys, types, nullability)
  - docs/legacy_compressed_json_rules.md  (why legacy JSON looked inlined)
  - docs/in_memory_pipeline.md            (overall architecture)
  - docs/fcpxml_rules.md                  (writer consumes canonical JSON; not the DB)

Core principle (repeated):
  • Authoritative-first source resolution (end of UMID chain).
  • Path fidelity (no normalization).
  • No filtering of OperationGroups (include filler effects).
  • Required keys always present; unknown values are null.

This wrapper exists to keep the program structure obvious and prevent any drift
from the spec. Implementation lives in src/build_canonical.py.
"""

from __future__ import annotations

import argparse
import json
from typing import Any

# Import the SPEC-FIRST builder (no logic here).
from .build_canonical import build_canonical_from_aaf  # type: ignore


def main(argv: list[str] | None = None) -> int:
    """
    CLI:
      python -m src.parse_aaf /path/to/timeline.aaf -o out.json

    Behavior:
      - Opens the AAF (delegated inside build_canonical_from_aaf).
      - Returns a dict matching docs/data_model_json.md exactly.
      - Prints to stdout or writes to a file.

    NOTE:
      - This file must not add ad-hoc fields or transform the dict in any way.
      - No traversal/extraction logic is allowed here.
    """
    ap = argparse.ArgumentParser(description="Parse AAF → canonical JSON (spec-first wrapper).")
    ap.add_argument("aaf", help="Path to AAF file")
    ap.add_argument("-o", "--out", default="-", help="Output JSON path (default: stdout)")
    args = ap.parse_args(argv)

    canon: dict[str, Any] = build_canonical_from_aaf(args.aaf)

    text = json.dumps(canon, indent=2)
    if args.out == "-" or args.out.lower() == "stdout":
        print(text)
    else:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
