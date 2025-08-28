#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_canonical.py — SPEC-FIRST SCAFFOLD (no implementation yet)

This module defines the public entrypoint and function contracts for building the
**canonical JSON** dict from an AAF file. It deliberately contains NO business
logic; instead it documents what MUST be implemented, referencing the project
specs. Implementers (human or LLM) must follow the docs exactly and not invent
ad-hoc behavior.

Authoritative specs:
  - docs/data_model_json.md            (canonical JSON schema; single source of truth)
  - docs/inspector_rule_pack.md        (timeline traversal, UMID resolution, effects)
  - docs/legacy_compressed_json_rules.md  (how the compressed JSON exporter inlined values)
  - docs/in_memory_pipeline.md         (architecture, inspector hooks, contracts)
  - docs/fcpxml_rules.md               (Resolve FCPXML 1.13 writer requirements)

CORE PRINCIPLE (repeat in every implementation):
  • **Authoritative-first**: For source fields (path, TapeID, DiskLabel, src TC/rate/drop),
    resolve to the **end of the UMID chain**:
      SourceClip → MasterMob → SourceMob → ImportDescriptor → Locator(URLString)
    Comp-level mirrors are **fallback only** if chain nodes are missing.
  • **Path fidelity**: Never normalize paths (UNC, percent-encoding, drive letters).
  • **No filtering**: Capture ALL OperationGroups (AVX/AFX/DVE), including filler effects.
  • **Nullability**: Required keys must exist; unknown values must be null (not omitted).
"""

from __future__ import annotations
from typing import Dict, Any, Iterable, Optional, Tuple, List
import argparse
import json

# External dependency (pyaaf2 is imported as "aaf2" in Python)
# DO NOT remove this; implementation will require it.
try:
    import aaf2  # type: ignore
except Exception:
    aaf2 = None  # Allowed in scaffold; real implementation must import pyaaf2 successfully.


# --------------------------- Public API ---------------------------

def build_canonical_from_aaf(aaf_path: str) -> Dict[str, Any]:
    """
    Open an AAF and return the **canonical JSON** dict per docs/data_model_json.md.

    DO NOT implement traversal ad-hoc. Follow:
      - docs/inspector_rule_pack.md  §1 Timeline selection & traversal
      - docs/inspector_rule_pack.md  §2 Event packing
      - docs/inspector_rule_pack.md  §3 Source resolution (authoritative-first)
      - docs/inspector_rule_pack.md  §4–5 Effects & Pan/Zoom stills
      - docs/inspector_rule_pack.md  §6 Nullability & precedence

    High-level algorithm (spec-only, no code here):
      1) Open AAF read-only.
      2) Select top-level CompositionMob (prefer name *.Exported.01) and picture slot.
      3) Derive timeline fps (slot.EditRate), tc_format (DF/NDF), start_tc_frames.
      4) Walk Sequence.Components in order (recurse nested Sequence), maintaining absolute
         timeline_start_frames and length_frames for each event.
      5) For each component:
         - SourceClip  → produce an event with "source" object (populated via UMID chain),
                         and effect = "(none)".
         - OperationGroup on filler → produce an event with source = null, and "effect" object
                         with name/parameters/keyframes/external_refs.
      6) Pack "project" and "timeline" objects with required keys (never omit).
      7) Return the dict.

    Returns:
      Dict[str, Any]: A structure that EXACTLY matches docs/data_model_json.md
                      (required keys, nullability, types).

    MUSTs:
      - **Authoritative-first** for source metadata (Locator URL, SourceMob TC/rate/drop).
      - Preserve path strings exactly (no normalization).
      - Capture ALL OperationGroups (no filtering), including filler effects.
      - For keyframes, store arrays of {"t": float seconds, "v": number|string}.

    MAY NOT:
      - Output partial/alternative shapes.
      - Normalize paths or rewrite slashes/drive letters/percent-encoding.
    """
    # TODO(impl):
    # - Open with aaf2.open(aaf_path, 'r')
    # - seq, fps, drop, start_frames, timeline_name = select_top_sequence(aaf)
    # - mob_map = build_mob_map(aaf)
    # - events = []
    # - for ev in walk_sequence_components(seq, fps):  # yields EvWrap (spec-defined)
    #       if ev.kind == "sourceclip":
    #           source = resolve_sourceclip(ev.node, mob_map)     # authoritative-first
    #           effect = make_none_effect()                       # "(none)"
    #           events.append(pack_event(ev, source, effect))
    #       elif ev.kind == "operationgroup_on_filler":
    #           effect = extract_operationgroup(ev.node)          # no filtering
    #           effect["on_filler"] = True
    #           events.append(pack_event(ev, None, effect))
    # - return pack_canonical_project(timeline_name, fps, drop, start_frames, events)
    raise NotImplementedError("Spec scaffold: implement per docs/inspector_rule_pack.md")


# --------------------------- Contracts (no logic) ---------------------------

def select_top_sequence(aaf) -> Tuple[Any, float, bool, int, str]:
    """
    Return (sequence_node, fps, is_drop, start_tc_frames, timeline_name).

    SPEC (do not implement here):
      - Pick the CompositionMob with name *.Exported.01 if present; else first CompositionMob.
      - Use the **picture** slot only (skip audio/data).
      - fps = float(slot.EditRate); is_drop from nearest timeline Timecode.drop.
      - start_tc_frames default 3600 (01:00:00:00 @ fps) if not explicitly available.

    See: docs/inspector_rule_pack.md §1
    """
    raise NotImplementedError


def walk_sequence_components(seq, fps: float) -> Iterable["EvWrap"]:
    """
    Yield EvWrap objects in **playback order**, flattening nested Sequences.

    EvWrap spec:
      - .kind ∈ {"sourceclip", "operationgroup_on_filler", "unknown"}
      - .node  → the underlying pyaaf2 object
      - .timeline_start_frames: int (absolute)
      - .length_frames: int
      - .index: 1-based stable index (ev_0001, ev_0002, ...)

    Rules:
      - Only picture track Sequence is traversed.
      - Maintain a running timeline offset (frames).
      - If component is a Sequence, recurse and continue linearization.
      - OperationGroup is considered "on_filler" when no SourceClip input is present.

    See: docs/inspector_rule_pack.md §1–2
    """
    raise NotImplementedError


def build_mob_map(aaf) -> Dict[str, Any]:
    """
    Return a dict mapping string mob_id/UMID → mob object.

    Purpose:
      - Speed up UMID chain traversal when resolving SourceClips.

    See: docs/inspector_rule_pack.md §3
    """
    raise NotImplementedError


def resolve_sourceclip(sc, mob_map) -> Dict[str, Any]:
    """
    Return the "source" object for a SourceClip event (authoritative-first).

    MUST populate (see docs/data_model_json.md → Source):
      - path: string|null                (from ImportDescriptor→Locator.URLString)
      - umid_chain: array<string>       (nearest → furthest)
      - tape_id: string|null            (UserComments → MobAttributeList; nearest wins)
      - disk_label: string|null         (_IMPORTDISKLABEL via _IMPORTSETTING/TaggedValueAttributeList)
      - src_tc_start_frames: int|null   (SourceMob.Timecode.start; frames @ source rate)
      - src_rate_fps: float             (SourceMob or slot edit rate)
      - src_drop: bool                  (SourceMob.Timecode.drop)

    RULES:
      - **Authoritative-first**: prefer end-of-chain values. Comp-level mirrors are fallback only.
      - Broken chain tolerated: emit nulls where unknown, never abort.
      - Preserve path fidelity: never normalize/alter the string.

    See: docs/inspector_rule_pack.md §3
    """
    raise NotImplementedError


def extract_operationgroup(op) -> Dict[str, Any]:
    """
    Return the "effect" object for an OperationGroup (AVX/AFX/DVE).

    MUST populate (see docs/data_model_json.md → Effect):
      - name: string                     (prefer _EFFECT_PLUGIN_NAME → _EFFECT_PLUGIN_CLASS → label)
      - on_filler: bool                  (the caller sets True when it’s on filler)
      - parameters: object               (static values; numbers/strings only)
      - keyframes:  object               (param -> [{ "t": float seconds, "v": number|string }])
      - external_refs: array             ([{ "kind": "image|matte|unknown", "path": string }])

    RULES:
      - **No filtering**: capture ALL OperationGroups (filler or not).
      - Pan & Zoom stills: attempt UTF-16LE decode on byte arrays; strip nulls; do not rewrite.
      - Path detection: if value looks like a path (file://, /, :\\), record in external_refs.

    See: docs/inspector_rule_pack.md §4–5
    """
    raise NotImplementedError


def pack_event(ev: "EvWrap", source: Optional[Dict[str, Any]], effect: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build one Event object per docs/data_model_json.md (required keys always present).

    - id: "ev_{index:04d}"
    - timeline_start_frames: int
    - length_frames: int
    - source: object|null
    - effect: object (for plain clips, must be "(none)" shape)

    See: docs/inspector_rule_pack.md §2; docs/data_model_json.md
    """
    raise NotImplementedError


def pack_canonical_project(
    timeline_name: str,
    fps: float,
    is_drop: bool,
    start_tc_frames: int,
    events: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Build the top-level canonical dict:
      {
        "project":  { name, edit_rate_fps, tc_format },
        "timeline": { name, start_tc_frames, events: [...] }
      }

    - tc_format: "DF" if is_drop else "NDF"
    - Required keys MUST be present even if values are null.

    See: docs/data_model_json.md
    """
    raise NotImplementedError


# --------------------------- Types (no behavior) ---------------------------

class EvWrap:
    """
    Lightweight carrier for traversal results.

    Fields:
      kind: str     # "sourceclip" | "operationgroup_on_filler" | "unknown"
      node: Any     # pyaaf2 object
      timeline_start_frames: int
      length_frames: int
      index: int    # 1-based, stable
    """
    __slots__ = ("kind", "node", "timeline_start_frames", "length_frames", "index")

    def __init__(self, kind: str, node: Any, start: int, length: int, index: int) -> None:
        self.kind = kind
        self.node = node
        self.timeline_start_frames = int(start)
        self.length_frames = int(length)
        self.index = int(index)


# --------------------------- CLI (spec harness) ---------------------------

def _cli() -> None:
    """
    Spec-only CLI harness. Prints or writes the canonical JSON.

    Usage (after implementation exists):
        python -m src.build_canonical /path/to/timeline.aaf -o out.json

    NOTE: This harness MUST NOT implement traversal here. It only calls
    build_canonical_from_aaf() when implemented.
    """
    ap = argparse.ArgumentParser(description="Build canonical JSON from an AAF (spec-first scaffold).")
    ap.add_argument("aaf", help="Path to AAF file")
    ap.add_argument("-o", "--out", default="-", help="Output JSON path (default: stdout)")
    args = ap.parse_args()

    canon = build_canonical_from_aaf(args.aaf)
    text = json.dumps(canon, indent=2)
    if args.out == "-" or args.out.lower() == "stdout":
        print(text)
    else:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)


if __name__ == "__main__":
    _cli()
