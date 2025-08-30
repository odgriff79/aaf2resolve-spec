#!/usr/bin/env python3

"""
write_fcpxml.py — SPEC-FIRST SCAFFOLD (no implementation yet)
"""

from __future__ import annotations
import argparse
import json

def write_fcpxml_from_canonical(
    canon: dict[str, any], out_path: str
) -> None:
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
    # TODO: implement actual FCPXML writing logic
    pass

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
