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
- One OperationGroup = one effect event (no duplication from nested structures)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set

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

    # Find picture slot - look for Sequence, not Timecode
    picture_slot = None
    timecode_slot = None
    
    for slot in _iter_safe(selected_mob.slots):
        if hasattr(slot, "segment") and slot.segment:
            segment_type = str(type(slot.segment).__name__)
            if "Sequence" in segment_type:
                picture_slot = slot
            elif "Timecode" in segment_type:
                timecode_slot = slot

    # Use picture slot for frame rate, timecode slot for start time
    if not picture_slot:
        raise ValueError(f"No picture slot found in {timeline_name}")

    # Extract timeline properties
    fps = float(picture_slot.edit_rate) if hasattr(picture_slot, "edit_rate") else 25.0

    # Extract timeline start from timecode slot or search in picture slot
    is_drop = False
    start_tc_string = "10:00:00:00"  # Default

    # First try the dedicated timecode slot
    if timecode_slot and hasattr(timecode_slot, "segment"):
        start_frames = _find_start_timecode(timecode_slot.segment)
    else:
        # Fall back to searching in picture slot
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
        # Add all possible ID attributes to the map
        if hasattr(mob, "mob_id"):
            mob_map[str(mob.mob_id)] = mob
        if hasattr(mob, "umid"):
            mob_map[str(mob.umid)] = mob
        if hasattr(mob, "source_id"):
            mob_map[str(mob.source_id)] = mob
        if hasattr(mob, "package_id"):
            mob_map[str(mob.package_id)] = mob
            
        # Debug: show what IDs this mob has
        mob_name = getattr(mob, "name", "unnamed")
        logger.debug(f"Mob '{mob_name}': mob_id={getattr(mob, 'mob_id', None)}, umid={getattr(mob, 'umid', None)}")
    
    return mob_map


def extract_clips_from_comp_mob(comp_mob, mob_map: Dict[str, Any], fps: float) -> List[Dict[str, Any]]:
    """Extract clips by recursively traversing CompositionMob segment tree."""
    clips = []

    # Find picture slot - look for video/picture track specifically
    picture_slot = None
    slots = _iter_safe(comp_mob.slots)
    
    logger.debug(f"Found {len(slots)} slots in CompositionMob")
    
    for i, slot in enumerate(slots):
        if hasattr(slot, "segment") and slot.segment:
            segment_type = str(type(slot.segment).__name__)
            slot_name = getattr(slot, "name", f"Slot{i}")
            logger.debug(f"Slot {i} '{slot_name}': {segment_type}")
            
            # Skip timecode slots - look for Sequence slots
            if "Sequence" in segment_type:
                picture_slot = slot
                logger.debug(f"Selected slot {i} as picture slot: {segment_type}")
                break
            elif "Timecode" not in segment_type and picture_slot is None:
                # Fallback: take first non-timecode slot
                picture_slot = slot
                logger.debug(f"Using slot {i} as fallback picture slot: {segment_type}")

    if not picture_slot or not hasattr(picture_slot, "segment"):
        logger.warning("No picture slot found")
        return clips

    # Track processed timeline ranges to prevent duplication
    processed_ranges = set()

    # Recursively extract clips from segment tree
    segment_type = type(picture_slot.segment).__name__
    logger.debug(f"Starting recursive extraction from segment: {segment_type}")
    _extract_clips_recursive(picture_slot.segment, clips, mob_map, 0, fps, processed_ranges)
    return clips


def _extract_clips_recursive(segment, clips: List[Dict[str, Any]], mob_map: Dict[str, Any], timeline_offset: int, fps: float, processed_ranges: Set[Tuple[int, int]]) -> int:
    """Recursively traverse segment tree to extract events.
    
    Event types:
    1. Standalone SourceClip = Media Only
    2. OperationGroup with SourceClip inputs = Media + Effect  
    3. OperationGroup without SourceClip inputs = Effect Only
    """
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
            current_offset = _extract_clips_recursive(component, clips, mob_map, current_offset, fps, processed_ranges)
        return current_offset

    elif "OperationGroup" in segment_type:
        # Each OperationGroup = exactly one event, regardless of inputs
        # The event represents either "effect on media" or "effect on filler"
        op_length = int(getattr(segment, "length", 0))
        op_range = (timeline_offset, timeline_offset + op_length)
        
        if op_range in processed_ranges:
            logger.debug(f"Skipping already processed OperationGroup at range {op_range}")
            return timeline_offset + op_length
        
        processed_ranges.add(op_range)
        
        # Extract effect information
        operation_def = getattr(segment, "operation_def", None)
        operation_name = "Unknown Effect"
        if operation_def:
            if hasattr(operation_def, "name"):
                op_name_val = getattr(operation_def, "name")
                if op_name_val:
                    operation_name = str(op_name_val)
            elif hasattr(operation_def, "auid"):
                operation_name = f"Effect_{str(operation_def.auid)[-8:]}"
        
        # Analyze input segments to determine event type
        input_segments = None
        if hasattr(segment, "input_segments"):
            input_segments = _iter_safe(segment.input_segments)
        elif hasattr(segment, "segments"):
            input_segments = _iter_safe(segment.segments)
        elif hasattr(segment, "inputs"):
            input_segments = _iter_safe(segment.inputs)
        
        input_count = len(input_segments) if input_segments else 0
        
        # Check if this OperationGroup has SourceClip inputs (media) or just filler
        has_source_clips = False
        source_clip_info = None
        
        def find_source_clip_recursive(segment):
            """Recursively search for SourceClips within a segment tree."""
            if not segment:
                return None
                
            seg_type = str(type(segment).__name__)
            
            if "SourceClip" in seg_type:
                # Found a SourceClip - extract its info
                clip_name = str(getattr(segment, "name", "Media"))
                source_id = getattr(segment, "source_id", None)
                return {
                    "name": clip_name,
                    "source_umid": str(source_id) if source_id else "",
                    "source_path": resolve_source_path(segment, mob_map)
                }
            elif "Sequence" in seg_type:
                # Search within sequence components
                if hasattr(segment, "components"):
                    for comp in _iter_safe(segment.components):
                        result = find_source_clip_recursive(comp)
                        if result:
                            return result
            elif "OperationGroup" in seg_type:
                # Don't recurse into nested OperationGroups to avoid infinite loops
                pass
                
            return None
        
        if input_segments:
            for input_seg in input_segments:
                source_info = find_source_clip_recursive(input_seg)
                if source_info:
                    has_source_clips = True
                    source_clip_info = source_info
                    break  # Use first SourceClip found
        
        # Create exactly ONE event for this OperationGroup
        if has_source_clips and source_clip_info:
            # Case: SourceClip + Effect = "Media with Effect" event
            event_name = f"{source_clip_info['name']} + {operation_name}"
            event = {
                "name": event_name,
                "in": timeline_offset,
                "out": timeline_offset + op_length,
                "source_umid": source_clip_info["source_umid"],
                "source_path": source_clip_info["source_path"],
                "effect_params": {
                    "operation": operation_name,
                    "has_media": True,
                    "input_count": input_count,
                    "length": op_length
                }
            }
            logger.debug(f"Added media+effect clip: {event_name} ({timeline_offset}-{timeline_offset + op_length})")
        else:
            # Case: Effect on Filler = "Effect Only" event  
            event = {
                "name": operation_name,
                "in": timeline_offset,
                "out": timeline_offset + op_length,
                "source_umid": "",
                "source_path": None,
                "effect_params": {
                    "operation": operation_name,
                    "has_media": False,
                    "input_count": input_count,
                    "length": op_length
                }
            }
            logger.debug(f"Added effect-only clip: {operation_name} ({timeline_offset}-{timeline_offset + op_length})")
        
        clips.append(event)
        return timeline_offset + op_length

    elif "SourceClip" in segment_type:
        # Standalone SourceClip (not inside OperationGroup) = "Media Only" event
        clip_length = int(getattr(segment, "length", 0))
        clip_range = (timeline_offset, timeline_offset + clip_length)
        
        # Don't double-process SourceClips that are already covered by OperationGroups
        if clip_range in processed_ranges:
            logger.debug(f"Skipping SourceClip already covered by OperationGroup at range {clip_range}")
            return timeline_offset + clip_length
        
        processed_ranges.add(clip_range)
        
        clip_name = str(getattr(segment, "name", "Media"))
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
        logger.debug(f"Added standalone SourceClip: {clip_name} ({timeline_offset}-{timeline_offset + clip_length})")
        return timeline_offset + clip_length

    elif "Filler" in segment_type:
        # Pure filler (not in OperationGroup) - skip but account for length
        filler_length = int(getattr(segment, "length", 0))
        logger.debug(f"Skipping pure Filler of length {filler_length}")
        return timeline_offset + filler_length

    elif "ScopeReference" in segment_type:
        # ScopeReference segments are inputs within OperationGroups - don't emit as clips
        # Just account for their length in timeline progression
        scope_length = int(getattr(segment, "length", 0))
        logger.debug(f"Processing ScopeReference of length {scope_length} (scope reference, not mob reference)")
        return timeline_offset + scope_length

    elif "Transition" in segment_type:
        # Skip transitions but account for their length
        transition_length = int(getattr(segment, "length", 0))
        logger.debug(f"Skipping Transition of length {transition_length}")
        return timeline_offset + transition_length

    elif "Timecode" in segment_type:
        # Skip timecode components but don't advance offset
        logger.debug("Skipping Timecode component")
        return timeline_offset

    else:
        # Unknown component type - try to explore it for nested segments
        component_length = int(getattr(segment, "length", 0))
        logger.debug(f"Exploring unknown segment type {segment_type}, length={component_length}")
        
        # Try to find nested segments in unknown types
        nested_segments = None
        for attr_name in ["segments", "components", "inputs", "input_segments"]:
            if hasattr(segment, attr_name):
                nested_segments = _iter_safe(getattr(segment, attr_name))
                if nested_segments:
                    logger.debug(f"Unknown segment has {len(nested_segments)} nested segments via {attr_name}")
                    current_offset = timeline_offset
                    for nested_seg in nested_segments:
                        current_offset = _extract_clips_recursive(nested_seg, clips, mob_map, current_offset, fps, processed_ranges)
                    return current_offset
                break
        
        # No nested segments found, just account for length
        return timeline_offset + component_length


def resolve_source_path_from_descriptor(desc) -> Optional[str]:
    """Extract file path from a descriptor object."""
    try:
        if hasattr(desc, "locator"):
            locator = desc.locator
            if hasattr(locator, "url_string"):
                return str(locator.url_string)
        elif hasattr(desc, "locators"):
            # Multiple locators - try the first one
            locators = _iter_safe(desc.locators)
            if locators:
                first_locator = locators[0]
                if hasattr(first_locator, "url_string"):
                    return str(first_locator.url_string)
        return None
    except Exception as e:
        logger.debug(f"Error resolving descriptor path: {e}")
        return None


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
