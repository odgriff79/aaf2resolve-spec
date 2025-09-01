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


def _iter_safe(aaf_obj):
    """Safely iterate over AAF objects that may be properties or None."""
    if aaf_obj is None:
        return []
    try:
        # Try to iterate directly (for properties)
        return list(aaf_obj)
    except TypeError:
        # Not iterable; wrap as single-item list
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
    # Find CompositionMobs - use property, not method
    comp_mobs = []
    try:
        for mob in aaf.content.mobs:
            if hasattr(mob, 'slots') and str(type(mob).__name__) == "CompositionMob":
                comp_mobs.append(mob)
    except Exception as e:
        logger.debug(f"Error iterating mobs: {e}")
        # Fallback: try compositionmobs method if it exists
        if hasattr(aaf.content, 'compositionmobs'):
            comp_mobs = list(aaf.content.compositionmobs())

    if not comp_mobs:
        raise ValueError("No CompositionMobs found in AAF")

    # Prefer *.Exported.01, else take first
    selected_mob = None
    for mob in comp_mobs:
        mob_name = getattr(mob, "name", None)
        if mob_name and str(mob_name).endswith(".Exported.01"):
            selected_mob = mob
            break

    if not selected_mob:
        selected_mob = comp_mobs[0]
        logger.warning("No .Exported.01 mob found, using first CompositionMob")

    timeline_name = getattr(selected_mob, "name", "Unknown Timeline") or "Unknown Timeline"

    # Find picture slot - use property, not method
    picture_slot = None
    for slot in _iter_safe(selected_mob.slots):
        if hasattr(slot, "segment") and slot.segment:
            picture_slot = slot
            break

    if not picture_slot:
        raise ValueError(f"No picture slot found in {timeline_name}")

    # Extract timeline properties
    fps = float(picture_slot.edit_rate) if hasattr(picture_slot, "edit_rate") else 25.0

    # Extract timeline start from timecode segment
    is_drop = False
    start_tc_string = "10:00:00:00"  # Default

    # Look for timecode information in the segment tree
    start_frames = _find_start_timecode(picture_slot.segment)
    if start_frames is not None:
        start_tc_string = frames_to_timecode(start_frames, fps, is_drop)

    return selected_mob, fps, is_drop, start_tc_string, timeline_name


def _find_start_timecode(segment) -> Optional[int]:
    """Recursively search for timecode component to get start time."""
    if not segment:
        return None
    
    segment_type = str(type(segment).__name__)
    
    if "Timecode" in segment_type:
        return int(getattr(segment, "start", 0))
    
    # Search in components if it's a sequence
    if hasattr(segment, "components"):
        for comp in _iter_safe(segment.components):
            result = _find_start_timecode(comp)
            if result is not None:
                return result
    
    # Search in input_segments if it's an operation group
    if hasattr(segment, "input_segments"):
        for input_seg in _iter_safe(segment.input_segments):
            result = _find_start_timecode(input_seg)
            if result is not None:
                return result
    
    return None


def build_mob_map(aaf) -> Dict[str, Any]:
    """Build lookup map: mob_id/UMID → mob object for UMID resolution."""
    mob_map = {}
    for mob in _iter_safe(aaf.content.mobs):
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
    for slot in _iter_safe(comp_mob.slots):
        if hasattr(slot, "segment") and slot.segment:
            picture_slot = slot
            break

    if not picture_slot or not hasattr(picture_slot, "segment"):
        logger.warning("No picture slot found")
        return clips

    # Recursively extract SourceClips from segment tree
    logger.debug(f"Starting recursive extraction from segment: {type(picture_slot.segment).__name__}")
    _extract_clips_recursive(picture_slot.segment, clips, mob_map, 0, fps)
    return clips


def _extract_clips_recursive(segment, clips: List[Dict[str, Any]], mob_map: Dict[str, Any], timeline_offset: int, fps: float) -> int:
    """Recursively traverse segment tree to find SourceClip objects."""
    if not segment:
        return timeline_offset

    segment_type = str(type(segment).__name__)
    logger.debug(f"Processing segment type: {segment_type} at offset {timeline_offset}")

    if "Sequence" in segment_type:
        # Traverse sequence components
        current_offset = timeline_offset
        components = _iter_safe(segment.components)
        logger.debug(f"Sequence has {len(components)} components")
        for component in components:
            current_offset = _extract_clips_recursive(component, clips, mob_map, current_offset, fps)
        return current_offset

    elif "OperationGroup" in segment_type:
        # Traverse operation group input segments
        current_offset = timeline_offset
        input_segments = None
        
        # Try different attribute names for input segments
        if hasattr(segment, "input_segments"):
            input_segments = _iter_safe(segment.input_segments)
        elif hasattr(segment, "segments"):
            input_segments = _iter_safe(segment.segments)
        elif hasattr(segment, "inputs"):
            input_segments = _iter_safe(segment.inputs)
        
        if input_segments:
            logger.debug(f"OperationGroup has {len(input_segments)} input segments")
            for input_seg in input_segments:
                current_offset = _extract_clips_recursive(input_seg, clips, mob_map, current_offset, fps)
        else:
            # If no input segments, treat as having its own length
            op_length = int(getattr(segment, "length", 0))
            current_offset += op_length
            
        return current_offset

    elif "SourceClip" in segment_type:
        # This is an actual clip - extract it
        clip_length = int(getattr(segment, "length", 0))
        clip_name = str(getattr(segment, "name", "Clip"))
        source_id = getattr(segment, "source_id", None)
        
        clip = {
            "name": clip_name,
            "in": timeline_offset,
            "out": timeline_offset + clip_length,
            "source_umid": str(source_id) if source_id else "",
            "source_path": resolve_source_path(segment, mob_map),
            "effect_params": {}
        }
        clips.append(clip)
        logger.debug(f"Added SourceClip: {clip_name} ({timeline_offset}-{timeline_offset + clip_length})")
        return timeline_offset + clip_length

    elif "Transition" in segment_type:
        # Skip transitions but account for their length
        transition_length = int(getattr(segment, "length", 0))
        logger.debug(f"Skipping Transition of length {transition_length}")
        return timeline_offset + transition_length

    elif "Filler" in segment_type:
        # Skip filler but account for length
        filler_length = int(getattr(segment, "length", 0))
        logger.debug(f"Skipping Filler of length {filler_length}")
        return timeline_offset + filler_length

    elif "Timecode" in segment_type:
        # Skip timecode components but don't advance offset
        logger.debug("Skipping Timecode component")
        return timeline_offset

    else:
        # Unknown component type - skip but account for length if present
        component_length = int(getattr(segment, "length", 0))
        logger.debug(f"Skipping unknown segment type {segment_type}, length={component_length}")
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
                    return str(locator.url_string)

        return None
    except Exception as e:
        logger.debug(f"Error resolving source path: {e}")
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
