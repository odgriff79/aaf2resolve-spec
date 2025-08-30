#!/usr/bin/env python3
<<<<<<< HEAD

=======
>>>>>>> 92a31e6 (Fix all lint/style issues: modernize types, wrap long lines, and auto-format)
"""
write_fcpxml.py — SPEC-FIRST SCAFFOLD (no implementation yet)
"""

from __future__ import annotations
<<<<<<< HEAD
import argparse
import json

def write_fcpxml_from_canonical(
    canon: dict[str, any], out_path: str
) -> None:
=======

import argparse
import json
from typing import Any

# --------------------------- Public API ---------------------------


def write_fcpxml_from_canonical(canon: dict[str, Any], out_path: str) -> None:
>>>>>>> 92a31e6 (Fix all lint/style issues: modernize types, wrap long lines, and auto-format)
    """
    Write an FCPXML 1.13 document to `out_path`, consuming the canonical dict.

    - Effects on filler become appropriate generator/adjustment/contextual nodes
      (per doc), and include any parameters that cleanly map (timing preserved).
    - If an effect or parameter has no safe mapping, retain minimal representation
      rather than guessing.

    MUSTS:
    - Compute:
        * timeline frameDuration
        * project tcStart (seconds fraction corresponding to start_tc_frames @ fps,
          honoring DF/NDF)
    - Create assets for unique source.path values (null-safe handling).
    - Emit timeline items in canonical order; convert frames→seconds using timeline fps.
    """
<<<<<<< HEAD
    # TODO: implement actual FCPXML writing logic
    pass
=======
    raise NotImplementedError("Spec scaffold: implement per docs/fcpxml_rules.md")


# --------------------------- CLI (spec harness) ---------------------------


def main(argv: list[str] | None = None) -> int:
    """
    CLI:
      python -m src.write_fcpxml canonical.json -o timeline.fcpxml

    Behavior:
      - Loads canonical JSON from file.
      - Emits FCPXML 1.13 per docs/fcpxml_rules.md to the output path.

    NOTE:
      - This CLI must not alter or enrich the canonical dict.
      - No DB/AAF access here; this is a pure JSON→XML transform.
    """
    ap = argparse.ArgumentParser(
        description="Write FCPXML 1.13 from canonical JSON (spec-first scaffold)."
    )
    ap.add_argument("canon_json", help="Path to canonical JSON file")
    ap.add_argument("-o", "--out", required=True, help="Output FCPXML path")
    args = ap.parse_args(argv)

    with open(args.canon_json, encoding="utf-8") as f:
        canon: dict[str, Any] = json.load(f)

    write_fcpxml_from_canonical(canon, args.out)
    return 0

>>>>>>> 92a31e6 (Fix all lint/style issues: modernize types, wrap long lines, and auto-format)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Convert canonical JSON to FCPXML 1.13"
    )
    ap.add_argument("canon_json", help="Path to input canonical JSON")
    ap.add_argument("out", help="Path to output FCPXML")
    args = ap.parse_args()
    with open(args.canon_json, encoding="utf-8") as f:
        canon: dict[str, any] = json.load(f)
    write_fcpxml_from_canonical(canon, args.out)
