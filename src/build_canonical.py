#!/usr/bin/env python3
"""
Builds the in-memory canonical dict from an AAF file.

Spec:
  - docs/data_model_json.md
  - docs/inspector_rule_pack.md
"""

from typing import Dict, Any, List, Tuple
import argparse
import json
import aaf2  # pyaaf2

def select_top_sequence(aaf) -> Tuple[object, float, bool, int]:
    """Return (composition_sequence, fps, drop, start_tc_frames)."""
    # TODO: implement per rule §1
    raise NotImplementedError

def walk_sequence_components(seq, fps) -> List[object]:
    """Yield typed wrappers with .kind, .node, .timeline_start_frames, .length_frames."""
    # TODO: implement per rule §1–2
    raise NotImplementedError

def build_mob_map(aaf) -> dict:
    """Map of mob_id -> mob."""
    # TODO: implement
    return {}

def resolve_sourceclip(sc, mob_map) -> Dict[str, Any]:
    """Return the Source object per schema."""
    # TODO: implement rule §3
    raise NotImplementedError

def extract_operationgroup(op) -> Dict[str, Any]:
    """Return the Effect object per schema."""
    # TODO: implement rule §4–5
    raise NotImplementedError

def pack_event(ev, source, effect) -> Dict[str, Any]:
    # TODO: construct the Event object
    raise NotImplementedError

def pack_canonical_project(comp, fps, drop, start_frames, events) -> Dict[str, Any]:
    # TODO: construct the top-level project+timeline dict
    raise NotImplementedError

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("aaf")
    ap.add_argument("-o", "--out", default="-")
    args = ap.parse_args()

    canon = build_canonical_from_aaf(args.aaf)
    text = json.dumps(canon, indent=2)
    if args.out == "-" or args.out.lower() == "stdout":
        print(text)
    else:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)

if __name__ == "__main__":
    main()
