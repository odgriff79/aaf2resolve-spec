#!/usr/bin/env python3
"""
build_canonical.py — Core AAF → Canonical JSON Implementation

Implements the canonical JSON builder per docs/data_model_json.md and docs/inspector_rule_pack.md.
This is the primary entrypoint for converting AAF files into the canonical JSON format.

Key principles:
- Proper AAF source resolution via mob chain walking
- OperationGroup + nested SourceClip = single Media+Effect event
- Follow UMID chain to ImportDescriptor for true source info
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

    Follows proper AAF source resolution principles:
    - Walk mob chains to find true sources
    - Combine OperationGroups with resolved source info
    - Emit Media+Effect events

    Args:
        aaf_path: Path to AAF file

    Returns:
        Canonical JSON dict matching docs/data_model_json.md schema
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

            # Step 3: Extract events using proper source resolution
            clips = extract_events_with_source_resolution(comp, mob_map, fps)
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
    """Select top-level CompositionMob and extract timeline metadata."""
    # Find CompositionMobs
    comp_mobs = []
    try:
        for mob in aaf.content.mobs:
            if hasattr(mob, 'slots') and str(type(mob).__name__) == "CompositionMob":
                comp_mobs.append(mob)
    except Exception as e:
        logger.debug(f"Error iterating mobs: {e}")
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

    if not picture_slot:
        raise ValueError(f"No picture slot found in {timeline_name}")

    # Extract timeline properties
    fps = float(picture_slot.edit_rate) if hasattr(picture_slot, "edit_rate") else 25.0

    # Extract timeline start from timecode slot
    is_drop = False
    start_tc_string = "10:00:00:00"  # Default

    if timecode_slot and hasattr(timecode_slot, "segment"):
        start_frames = _find_start_timecode(timecode_slot.segment)
    else:
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
    
    if hasattr(segment, "components"):
        for comp in _iter_safe(segment.components):
            result = _find_start_timecode(comp)
            if result is not None:
                return result
    
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
    
    return mob_map


def extract_events_with_source_resolution(comp_mob, mob_map: Dict[str, Any], fps: float) -> List[Dict[str, Any]]:
    """Extract events using proper AAF source resolution."""
    clips = []

    # Find picture slot
    picture_slot = None
    slots = _iter_safe(comp_mob.slots)
    
    for i, slot in enumerate(slots):
        if hasattr(slot, "segment") and slot.segment:
            segment_type = str(type(slot.segment).__name__)
            if "Sequence" in segment_type:
                picture_slot = slot
                break

    if not picture_slot or not hasattr(picture_slot, "segment"):
        logger.warning("No picture slot found")
        return clips

    # Process the timeline sequence
    _process_sequence(picture_slot.segment, clips, mob_map, 0, fps)
    return clips


def _process_sequence(segment, clips: List[Dict[str, Any]], mob_map: Dict[str, Any], timeline_offset: int, fps: float) -> int:
    """Process a sequence and its components."""
    if not segment or not hasattr(segment, "components"):
        return timeline_offset
    
    current_offset = timeline_offset
    components = _iter_safe(segment.components)
    
    for component in components:
        current_offset = _process_component(component, clips, mob_map, current_offset, fps)
    
    return current_offset


def _process_component(segment, clips: List[Dict[str, Any]], mob_map: Dict[str, Any], timeline_offset: int, fps: float) -> int:
    """Process a single timeline component."""
    if not segment:
        return timeline_offset

    segment_type = str(type(segment).__name__)
    segment_length = int(getattr(segment, "length", 0))
    
    if "OperationGroup" in segment_type:
        # Each OperationGroup should produce one Media+Effect event
        _process_operation_group(segment, clips, mob_map, timeline_offset, fps)
        
    elif "SourceClip" in segment_type:
        # Standalone SourceClip (rare in modern AAF)
        _process_source_clip(segment, clips, mob_map, timeline_offset, fps, effect_name="N/A")
        
    elif "Filler" in segment_type:
        # Pure filler - skip
        logger.debug(f"Skipping Filler at {timeline_offset}, length {segment_length}")
        
    elif "Sequence" in segment_type:
        # Nested sequence - process recursively
        return _process_sequence(segment, clips, mob_map, timeline_offset, fps)
    
    return timeline_offset + segment_length


def _process_operation_group(operation_group, clips: List[Dict[str, Any]], mob_map: Dict[str, Any], timeline_offset: int, fps: float):
    """Process an OperationGroup by finding its nested SourceClip and combining with effect info."""
    
    # Extract effect information
    operation_def = getattr(operation_group, "operation_def", None)
    effect_name = "Unknown Effect"
    if operation_def:
        if hasattr(operation_def, "name"):
            op_name_val = getattr(operation_def, "name")
            if op_name_val:
                effect_name = str(op_name_val)
        elif hasattr(operation_def, "auid"):
            effect_name = f"Effect_{str(operation_def.auid)[-8:]}"
    
    # Find nested SourceClip via recursive search
    source_clip = _find_nested_source_clip(operation_group)
    
    if source_clip:
        # Process the SourceClip with effect context
        _process_source_clip(source_clip, clips, mob_map, timeline_offset, fps, effect_name)
        logger.debug(f"Added Media+Effect event: SourceClip + {effect_name} at {timeline_offset}")
    else:
        # No SourceClip found - this is an effect on filler
        op_length = int(getattr(operation_group, "length", 0))
        filler_event = {
            "name": effect_name,
            "in": timeline_offset,
            "out": timeline_offset + op_length,
            "source_umid": "FX_ON_FILLER",
            "source_path": None,
            "effect_params": {
                "operation": effect_name,
                "is_filler_effect": True,
                "length": op_length
            }
        }
        clips.append(filler_event)
        logger.debug(f"Added FX_ON_FILLER event: {effect_name} at {timeline_offset}")


def _find_nested_source_clip(node):
    """Recursively find SourceClip nested anywhere within a node."""
    if not node:
        return None
    
    node_type = str(type(node).__name__)
    
    # Found it!
    if "SourceClip" in node_type:
        return node
    
    # Search all possible child containers
    for attr_name in ["input_segments", "segments", "inputs", "components"]:
        if hasattr(node, attr_name):
            children = _iter_safe(getattr(node, attr_name))
            for child in children:
                result = _find_nested_source_clip(child)
                if result:
                    return result
    
    # Check single nested segment
    if hasattr(node, "segment") and getattr(node, "segment"):
        return _find_nested_source_clip(node.segment)
    
    return None


def _process_source_clip(source_clip, clips: List[Dict[str, Any]], mob_map: Dict[str, Any], timeline_offset: int, fps: float, effect_name: str):
    """Process a SourceClip by walking the mob chain to resolve true source."""
    
    clip_length = int(getattr(source_clip, "length", 0))
    source_id = getattr(source_clip, "source_id", None)
    
    if not source_id:
        logger.warning(f"SourceClip at {timeline_offset} has no source_id")
        return
    
    # Walk the mob chain to find true source
    resolved_source = walk_mob_chain(str(source_id), mob_map)
    
    if resolved_source:
        clip_name = resolved_source.get("clip_name", "Unknown Media")
        source_path = resolved_source.get("source_path")
        source_umid = resolved_source.get("source_umid", str(source_id))
        tape_id = resolved_source.get("tape_id")
        disk_label = resolved_source.get("disk_label")
    else:
        clip_name = "Unresolved Media"
        source_path = None
        source_umid = str(source_id)
        tape_id = None
        disk_label = None
    
    # Create event combining media + effect
    event_name = f"{clip_name}"
    if effect_name != "N/A":
        event_name = f"{clip_name} + {effect_name}"
    
    event = {
        "name": event_name,
        "in": timeline_offset,
        "out": timeline_offset + clip_length,
        "source_umid": source_umid,
        "source_path": source_path,
        "effect_params": {
            "operation": effect_name if effect_name != "N/A" else "",
            "tape_id": tape_id,
            "disk_label": disk_label,
            "length": clip_length
        }
    }
    
    clips.append(event)


def walk_mob_chain(mob_id: str, mob_map: Dict[str, Any], visited: Optional[set] = None) -> Optional[Dict[str, Any]]:
    """Walk the mob chain following SourceIDs until reaching ImportDescriptor."""
    if visited is None:
        visited = set()
    
    if mob_id in visited:
        logger.warning(f"Circular reference detected in mob chain: {mob_id}")
        return None
    
    visited.add(mob_id)
    mob = mob_map.get(mob_id)
    
    if not mob:
        logger.debug(f"Mob not found: {mob_id}")
        return None
    
    # Check if this mob has an ImportDescriptor (end of chain)
    if hasattr(mob, "descriptor"):
        descriptor = mob.descriptor
        if hasattr(descriptor, "locator") or (hasattr(descriptor, "locators") and _iter_safe(descriptor.locators)):
            # Found ImportDescriptor - extract source info
            return extract_source_info_from_mob(mob)
    
    # Look for next mob in chain via SourceClip
    next_mob_id = find_next_mob_in_chain(mob)
    
    if next_mob_id:
        # Continue walking the chain
        result = walk_mob_chain(next_mob_id, mob_map, visited)
        if result:
            return result
    
    # Fallback: use current mob if no chain continuation
    return extract_source_info_from_mob(mob)


def find_next_mob_in_chain(mob) -> Optional[str]:
    """Find the next MobID in the chain by looking for SourceClips in slots."""
    if not hasattr(mob, "slots"):
        return None
    
    for slot in _iter_safe(mob.slots):
        if hasattr(slot, "segment") and slot.segment:
            segment = slot.segment
            
            # Look for SourceClip in segment
            source_clip = _find_nested_source_clip(segment)
            if source_clip:
                next_id = getattr(source_clip, "source_id", None)
                if next_id:
                    return str(next_id)
    
    return None


def extract_source_info_from_mob(mob) -> Dict[str, Any]:
    """Extract source information from a mob."""
    source_info = {
        "clip_name": "Unknown Media",
        "source_path": None,
        "source_umid": str(getattr(mob, "mob_id", "")),
        "tape_id": None,
        "disk_label": None
    }
    
    # Get mob name
    mob_name = getattr(mob, "name", None)
    if mob_name:
        source_info["clip_name"] = str(mob_name)
    
    # Extract file path from descriptor
    if hasattr(mob, "descriptor"):
        descriptor = mob.descriptor
        
        # Try locator
        if hasattr(descriptor, "locator"):
            locator = descriptor.locator
            if hasattr(locator, "url_string"):
                url_string = str(locator.url_string)
                source_info["source_path"] = url_string
                # Extract filename from path
                try:
                    import urllib.parse
                    parsed = urllib.parse.urlparse(url_string)
                    if parsed.path:
                        source_info["clip_name"] = os.path.basename(parsed.path)
                except:
                    pass
        
        # Try multiple locators
        elif hasattr(descriptor, "locators"):
            locators = _iter_safe(descriptor.locators)
            if locators:
                first_locator = locators[0]
                if hasattr(first_locator, "url_string"):
                    url_string = str(first_locator.url_string)
                    source_info["source_path"] = url_string
                    try:
                        import urllib.parse
                        parsed = urllib.parse.urlparse(url_string)
                        if parsed.path:
                            source_info["clip_name"] = os.path.basename(parsed.path)
                    except:
                        pass
    
    # Extract TapeID and DiskLabel from attributes
    if hasattr(mob, "attributes"):
        attributes = _iter_safe(mob.attributes)
        for attr in attributes:
            if hasattr(attr, "name") and hasattr(attr, "value"):
                attr_name = str(attr.name)
                if "TapeID" in attr_name:
                    source_info["tape_id"] = str(attr.value)
                elif "DiskLabel" in attr_name:
                    source_info["disk_label"] = str(attr.value)
    
    return source_info


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
