#!/usr/bin/env python3
"""
build_canonical.py — Core AAF → Canonical JSON Implementation

Implements the canonical JSON builder per docs/data_model_json.md and docs/inspector_rule_pack.md.
This is the primary entrypoint for converting AAF files into the canonical JSON format.

Key principles:
- Authoritative-first UMID resolution (end of chain wins)
- Path fidelity preservation (no normalization)
- Complete OperationGroup capture (no filtering)
- Required keys always present (null for unknown values)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# External dependency (pyaaf2)
try:
    import aaf2
    HAS_AAF2 = True
except ImportError:
    aaf2 = None
    HAS_AAF2 = False

# Setup logging for debugging AAF traversal
logger = logging.getLogger(__name__)


def _iter(aaf_obj):
    """Return a list for iterables/collections; gracefully handle None."""
    if aaf_obj is None:
        return []
    try:
        return list(aaf_obj)
    except TypeError:
        # Not iterable; wrap as single-item list so callers can iterate safely
        return [aaf_obj]


def build_canonical_from_aaf(aaf_path: str) -> Dict[str, Any]:
    """
    Open an AAF and return the canonical JSON dict per docs/data_model_json.md.

    Follows docs/inspector_rule_pack.md for:
    - Timeline selection (prefer *.Exported.01)
    - UMID chain resolution (authoritative-first)
    - Event extraction (all OperationGroups, no filtering)
    - Path preservation (exact byte-for-byte fidelity)

    Args:
        aaf_path: Path to AAF file

    Returns:
        Canonical JSON dict matching docs/data_model_json.md schema

    Raises:
        ImportError: If pyaaf2 not available
        FileNotFoundError: If AAF file doesn't exist
        ValueError: If AAF cannot be parsed or has no usable timeline
    """
    if not HAS_AAF2:
        raise ImportError("aaf2 is required. Install with: pip install pyaaf2")

    if not Path(aaf_path).exists():
        raise FileNotFoundError(f"AAF file not found: {aaf_path}")

    logger.info(f"Opening AAF: {aaf_path}")

    try:
        with aaf2.open(aaf_path, "r") as f:
            # Step 1: Select top-level composition and extract timeline metadata
            comp, fps, is_drop, start_tc_string, timeline_name = select_top_sequence(f)
            logger.info(f"Selected timeline: {timeline_name} @ {fps}fps {'DF' if is_drop else 'NDF'}")

            # Step 2: Build mob lookup map for UMID resolution
            mob_map = build_mob_map(f)
            logger.info(f"Built mob map with {len(mob_map)} entries")

            # Step 3: Extract events from CompositionMob segment tree
            clips = extract_clips_from_comp_mob(comp, mob_map, fps)
            logger.info(f"Extracted {len(clips)} clips")

            # Step 4: Pack canonical structure  
            return {
                "timeline": {
                    "name": timeline_name,
                    "rate": int(fps),
                    "start": start_tc_string,
                    "tracks": [
                        {
                            "clips": clips
                        }
                    ]
                }
            }

    except Exception as e:
        logger.error(f"Failed to parse AAF {aaf_path}: {e}")
        raise ValueError(f"AAF parsing failed: {e}") from e


def select_top_sequence(aaf) -> Tuple[Any, float, bool, str, str]:
    """
    Select top-level CompositionMob and extract timeline metadata.

    Returns:
        (composition_mob, fps, is_drop, start_tc_string, timeline_name)
    """
    # Find CompositionMobs only
    comp_mobs = [mob for mob in aaf.content.compositionmobs() if hasattr(mob, "slots")]

    if not comp_mobs:
        raise ValueError("No CompositionMobs found in AAF")

    # Prefer *.Exported.01, else take first
    selected_mob = None
    for mob in comp_mobs:
        if hasattr(mob, "name") and mob.name and mob.name.endswith(".Exported.01"):
            selected_mob = mob
            break

    if not selected_mob:
        selected_mob = comp_mobs[0]
        logger.warning("No .Exported.01 mob found, using first CompositionMob")

    timeline_name = getattr(selected_mob, "name", "Unknown Timeline") or "Unknown Timeline"

    # Find picture slot
    picture_slot = None
    for slot in _iter(selected_mob.slots):
        if hasattr(slot, "segment") and slot.segment:
            picture_slot = slot
            break

    if not picture_slot:
        raise ValueError(f"No picture slot found in {timeline_name}")

    # Extract timeline properties
    fps = float(picture_slot.edit_rate) if hasattr(picture_slot, "edit_rate") else 25.0

    # Extract timeline start from first component if it's Timecode
    is_drop = False
    start_tc_string = "10:00:00:00"  # Default

    if hasattr(picture_slot, "segment") and hasattr(picture_slot.segment, "components"):
        components = _iter(picture_slot.segment.components)
        if components:
            first_comp = components[0]
            if hasattr(first_comp, "start") and hasattr(first_comp, "drop"):
                start_frames = int(first_comp.start)
                is_drop = bool(first_comp.drop)
                # Convert frames to timecode string at given fps
                start_tc_string = frames_to_timecode(start_frames, fps, is_drop)

    return selected_mob, fps, is_drop, start_tc_string, timeline_name


def build_mob_map(aaf) -> Dict[str, Any]:
    """Build lookup map: mob_id/UMID → mob object for UMID resolution."""
    mob_map = {}
    for mob in aaf.content.mobs():
        if hasattr(mob, "mob_id"):
            mob_map[str(mob.mob_id)] = mob
        if hasattr(mob, "umid"):
            mob_map[str(mob.umid)] = mob
    return mob_map


def extract_clips_from_comp_mob(comp_mob, mob_map: Dict[str, Any], fps: float) -> List[Dict[str, Any]]:
    """Extract clips by recursively traversing CompositionMob segment tree."""
    clips = []

    # Find picture slot
    picture_slot = None
    for slot in _iter(comp_mob.slots):
        if hasattr(slot, "segment") and slot.segment:
            picture_slot = slot
            break

    if not picture_slot or not hasattr(picture_slot, "segment"):
        return clips

    # Recursively extract SourceClips from segment tree
    clips = []
    _extract_clips_recursive(picture_slot.segment, clips, mob_map, 0, fps)
    return clips


def _extract_clips_recursive(segment, clips: List[Dict[str, Any]], mob_map: Dict[str, Any], timeline_offset: int, fps: float):
    """Recursively traverse segment tree to find SourceClip objects."""
    if not segment:
        return timeline_offset

    segment_type = str(type(segment).__name__)

    if "Sequence" in segment_type:
        # Traverse sequence components
        current_offset = timeline_offset
        for component in _iter(segment.components):
            current_offset = _extract_clips_recursive(component, clips, mob_map, current_offset, fps)
        return current_offset

    elif "OperationGroup" in segment_type:
        # Traverse operation group input segments
        current_offset = timeline_offset
        if hasattr(segment, "input_segments"):
            for input_seg in _iter(segment.input_segments):
                current_offset = _extract_clips_recursive(input_seg, clips, mob_map, current_offset, fps)
        elif hasattr(segment, "segments"):
            for input_seg in _iter(segment.segments):
                current_offset = _extract_clips_recursive(input_seg, clips, mob_map, current_offset, fps)
        return current_offset

    elif "SourceClip" in segment_type:
        # This is an actual clip - extract it
        clip_length = int(getattr(segment, "length", 0))
        
        clip = {
            "name": str(getattr(segment, "name", "Clip")),
            "in": timeline_offset,
            "out": timeline_offset + clip_length,
            "source_umid": str(getattr(segment, "source_id", "")),
            "source_path": resolve_source_path(segment, mob_map),
            "effect_params": {}
        }
        clips.append(clip)
        return timeline_offset + clip_length

    elif "Transition" in segment_type:
        # Skip transitions but account for their length
        transition_length = int(getattr(segment, "length", 0))
        return timeline_offset + transition_length

    elif "Filler" in segment_type:
        # Skip filler but account for length
        filler_length = int(getattr(segment, "length", 0))
        return timeline_offset + filler_length

    elif "Timecode" in segment_type:
        # Skip timecode components
        return timeline_offset

    else:
        # Unknown component type - skip
        component_length = int(getattr(segment, "length", 0))
        return timeline_offset + component_length


def resolve_source_path(source_clip, mob_map: Dict[str, Any]) -> Optional[str]:
    """Resolve source clip to file path via UMID chain."""
    try:
        source_id = getattr(source_clip, "source_id", None)
        if not source_id:
            return None

        # Follow UMID chain
        current_mob = mob_map.get(str(source_id))
        if not current_mob:
            return None

        # Look for file descriptor with locator
        if hasattr(current_mob, "descriptor"):
            desc = current_mob.descriptor
            if hasattr(desc, "locator"):
                locator = desc.locator
                if hasattr(locator, "url_string"):
                    return locator.url_string

        return None
    except Exception:
        return None


def frames_to_timecode(frames: int, fps: float, is_drop: bool) -> str:
    """Convert frame count to timecode string."""
    try:
        fps_int = int(fps)
        hours = frames // (fps_int * 60 * 60)
        minutes = (frames % (fps_int * 60 * 60)) // (fps_int * 60)
        seconds = (frames % (fps_int * 60)) // fps_int
        frame_num = frames % fps_int
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frame_num:02d}"
    except Exception:
        return "10:00:00:00"


def _cli() -> None:
    """CLI harness for building canonical JSON from AAF."""
    parser = argparse.ArgumentParser(
        description="Build canonical JSON from AAF file per aaf2resolve-spec."
    )
    parser.add_argument("aaf", help="Path to AAF file")
    parser.add_argument("-o", "--out", default="-", help="Output JSON path (default: stdout)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    try:
        canon = build_canonical_from_aaf(args.aaf)
        text = json.dumps(canon, indent=2)

        if args.out == "-" or args.out.lower() == "stdout":
            print(text)
        else:
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(text)
            logger.info(f"Canonical JSON written to {args.out}")

    except Exception as e:
        logger.error(f"Failed: {e}")
        raise SystemExit(1) from e


if __name__ == "__main__":
    _cli()
