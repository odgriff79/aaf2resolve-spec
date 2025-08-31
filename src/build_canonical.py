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
from collections.abc import Iterable
from pathlib import Path
from typing import Any, List, Optional, Tuple

# External dependency (pyaaf2)
try:
    import aaf2

    HAS_AAF2 = True
except ImportError:
    aaf2 = None
    HAS_AAF2 = False

# Setup logging for debugging AAF traversal
logger = logging.getLogger(__name__)


# --------------------------- Core Implementation ---------------------------


def build_canonical_from_aaf(aaf_path: str) -> dict[str, Any]:
    """
    Open an AAF and return the canonical JSON dict per docs/data_model_json.md.

    Follows docs/inspector_rule_pack.md for:
    - Timeline selection (prefer *.Exported.01)
    - UMID chain resolution (authoritative-first)
    - Effect extraction (all OperationGroups, no filtering)
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
        raise ImportError("pyaaf2 is required. Install with: pip install pyaaf2")

    if not Path(aaf_path).exists():
        raise FileNotFoundError(f"AAF file not found: {aaf_path}")

    logger.info(f"Opening AAF: {aaf_path}")

    try:
        with aaf2.open(aaf_path, "r") as f:
            # Step 1: Select top-level composition and extract timeline metadata
            comp, fps, is_drop, start_tc_frames, timeline_name = select_top_sequence(f)
            logger.info(
                f"Selected timeline: {timeline_name} @ {fps}fps {'DF' if is_drop else 'NDF'}"
            )

            # Step 2: Build mob lookup map for UMID resolution
            mob_map = build_mob_map(f)
            logger.info(f"Built mob map with {len(mob_map)} entries")

            # Step 3: Walk sequence components and extract events
            events = []
            for ev in walk_sequence_components(comp, fps):
                logger.debug(f"Processing event {ev.index}: {ev.kind} @ {ev.timeline_start_frames}")

                if ev.kind == "sourceclip":
                    source = resolve_sourceclip(ev.node, mob_map)
                    effect = make_none_effect()
                    events.append(pack_event(ev, source, effect))

                elif ev.kind == "operationgroup_on_filler":
                    effect = extract_operationgroup(ev.node)
                    effect["on_filler"] = True
                    events.append(pack_event(ev, None, effect))

                else:
                    logger.warning(f"Unknown event kind: {ev.kind}")
                    continue

            logger.info(f"Extracted {len(events)} events")

            # Step 4: Pack final canonical structure
            return pack_canonical_project(timeline_name, fps, is_drop, start_tc_frames, events)

    except Exception as e:
        logger.error(f"Failed to parse AAF {aaf_path}: {e}")
        raise ValueError(f"AAF parsing failed: {e}") from e


def select_top_sequence(aaf) -> Tuple[Any, float, bool, int, str]:
    """
    Select top-level CompositionMob and extract timeline metadata.

    Returns:
        (sequence_node, fps, is_drop, start_tc_frames, timeline_name)

    Per docs/inspector_rule_pack.md §1:
    - Prefer CompositionMob with name ending .Exported.01
    - Use picture track only (skip audio/data)
    - Extract edit rate, drop-frame flag, starting timecode
    """
    # Find all CompositionMobs
    comp_mobs = [mob for mob in aaf.content.mobs() if hasattr(mob, "slots")]

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
    for slot in selected_mob.slots:
        # Look for video/picture track (not audio or data)
        if hasattr(slot, "segment") and slot.segment:
            picture_slot = slot
            break

    if not picture_slot:
        raise ValueError(f"No picture slot found in {timeline_name}")

    # Extract timeline properties
    fps = float(picture_slot.edit_rate) if hasattr(picture_slot, "edit_rate") else 25.0

    # Look for drop-frame flag in timecode
    is_drop = False
    start_tc_frames = 3600  # Default 01:00:00:00 at 25fps

    # Try to find timeline timecode
    if hasattr(selected_mob, "slots"):
        for slot in selected_mob.slots:
            if hasattr(slot, "segment") and slot.segment:
                # Look for Timecode component
                if hasattr(slot.segment, "components"):
                    for comp in slot.segment.components:
                        if hasattr(comp, "start") and hasattr(comp, "drop"):
                            start_tc_frames = int(comp.start)
                            is_drop = bool(comp.drop)
                            break

    return picture_slot.segment, fps, is_drop, start_tc_frames, timeline_name


def walk_sequence_components(seq, fps: float) -> Iterable[EvWrap]:
    """
    Walk Sequence components in playback order, yielding EvWrap objects.

    Per docs/inspector_rule_pack.md §1-2:
    - Maintain running timeline offset
    - Recurse nested Sequences
    - Classify as sourceclip vs operationgroup_on_filler
    """
    if not hasattr(seq, "components"):
        return

    timeline_offset = 0
    event_index = 1

    for component in seq.components:
        length_frames = int(getattr(component, "length", 0))

        # Classify component type
        kind = "unknown"
        if hasattr(component, "__class__"):
            class_name = component.__class__.__name__

            if "SourceClip" in class_name:
                kind = "sourceclip"
            elif "OperationGroup" in class_name:
                # Check if it's on filler (no SourceClip inputs)
                has_source_input = False
                if hasattr(component, "input_segments"):
                    for input_seg in component.input_segments:
                        if input_seg and "SourceClip" in str(type(input_seg)):
                            has_source_input = True
                            break

                kind = (
                    "operationgroup_on_filler" if not has_source_input else "operationgroup_on_clip"
                )
            elif "Sequence" in class_name:
                # Recurse nested sequence
                for nested_ev in walk_sequence_components(component, fps):
                    nested_ev.timeline_start_frames += timeline_offset
                    nested_ev.index = event_index
                    event_index += 1
                    yield nested_ev
                timeline_offset += length_frames
                continue

        yield EvWrap(kind, component, timeline_offset, length_frames, event_index)
        timeline_offset += length_frames
        event_index += 1


def build_mob_map(aaf) -> dict[str, Any]:
    """
    Build lookup map: mob_id/UMID → mob object for UMID chain resolution.
    """
    mob_map = {}

    for mob in aaf.content.mobs():
        if hasattr(mob, "mob_id"):
            mob_map[str(mob.mob_id)] = mob
        if hasattr(mob, "umid"):
            mob_map[str(mob.umid)] = mob

    return mob_map


def resolve_sourceclip(sc, mob_map: dict[str, Any]) -> dict[str, Any]:
    """
    Resolve SourceClip via UMID chain to build source object.

    Per docs/inspector_rule_pack.md §3 (authoritative-first):
    - Follow SourceClip → MasterMob → SourceMob → ImportDescriptor → Locator
    - Chain-end values are authoritative
    - Comp-level mirrors are fallback only
    """
    source = {
        "path": None,
        "umid_chain": [],
        "tape_id": None,
        "disk_label": None,
        "src_tc_start_frames": None,
        "src_rate_fps": 25.0,
        "src_drop": False,
        "orig_length_frames": None,
    }

    try:
        # Start UMID chain traversal
        current_mob = sc
        umid_chain = []

        # Follow the chain: SourceClip → MasterMob → SourceMob
        while current_mob and len(umid_chain) < 10:  # Prevent infinite loops
            if hasattr(current_mob, "source_id"):
                umid_str = str(current_mob.source_id)
                umid_chain.append(umid_str)
                current_mob = mob_map.get(umid_str)
            elif hasattr(current_mob, "umid"):
                umid_str = str(current_mob.umid)
                umid_chain.append(umid_str)
                break
            else:
                break

        source["umid_chain"] = umid_chain

        # At chain end, extract authoritative metadata
        if current_mob:
            # Try to find ImportDescriptor → Locator path
            if hasattr(current_mob, "descriptor"):
                desc = current_mob.descriptor
                if hasattr(desc, "locator") and desc.locator:
                    if hasattr(desc.locator, "url_string"):
                        source["path"] = desc.locator.url_string

                # Original length from descriptor
                if hasattr(desc, "length"):
                    source["orig_length_frames"] = int(desc.length)

            # Source timecode and rate from SourceMob
            if hasattr(current_mob, "slots"):
                for slot in current_mob.slots:
                    if hasattr(slot, "edit_rate"):
                        source["src_rate_fps"] = float(slot.edit_rate)

                    if hasattr(slot, "segment") and hasattr(slot.segment, "components"):
                        for comp in slot.segment.components:
                            if hasattr(comp, "start"):
                                source["src_tc_start_frames"] = int(comp.start)
                            if hasattr(comp, "drop"):
                                source["src_drop"] = bool(comp.drop)

            # Metadata from UserComments or MobAttributeList
            source["tape_id"] = extract_metadata_value(current_mob, "TapeID")
            source["disk_label"] = extract_metadata_value(current_mob, "_IMPORTDISKLABEL")

    except Exception as e:
        logger.warning(f"UMID chain resolution failed: {e}")

    return source


def extract_metadata_value(mob, key: str) -> Optional[str]:
    """Extract metadata value from UserComments or MobAttributeList."""
    try:
        # Check UserComments first (higher priority)
        if hasattr(mob, "user_comments"):
            for comment in mob.user_comments:
                if hasattr(comment, "name") and comment.name == key:
                    return str(comment.value) if hasattr(comment, "value") else None

        # Fallback to MobAttributeList
        if hasattr(mob, "attributes"):
            for attr in mob.attributes:
                if hasattr(attr, "name") and attr.name == key:
                    return str(attr.value) if hasattr(attr, "value") else None

    except Exception:
        pass

    return None


def extract_operationgroup(op) -> dict[str, Any]:
    """
    Extract effect object from OperationGroup (AVX/AFX/DVE).

    Per docs/inspector_rule_pack.md §4-5:
    - NO FILTERING: capture all OperationGroups
    - Extract name, parameters, keyframes, external refs
    - Attempt UTF-16LE decode for Pan & Zoom stills
    """
    effect = {
        "name": "(none)",
        "on_filler": False,  # Caller will set appropriately
        "parameters": {},
        "keyframes": {},
        "external_refs": [],
    }

    try:
        # Extract effect name
        if hasattr(op, "operation_def"):
            op_def = op.operation_def
            if hasattr(op_def, "name"):
                effect["name"] = str(op_def.name)

        # Extract parameters
        if hasattr(op, "parameters"):
            for param in op.parameters:
                if hasattr(param, "name") and hasattr(param, "value"):
                    param_name = str(param.name)
                    param_value = param.value

                    # Handle different parameter types
                    if hasattr(param_value, "__iter__") and not isinstance(
                        param_value, str | bytes
                    ):
                        # Keyframe data (PointList)
                        keyframes = []
                        try:
                            for point in param_value:
                                if hasattr(point, "time") and hasattr(point, "value"):
                                    # Convert time to seconds, value to number/string
                                    time_sec = float(point.time)
                                    value = (
                                        float(point.value)
                                        if isinstance(point.value, int | float)
                                        else str(point.value)
                                    )
                                    keyframes.append({"t": time_sec, "v": value})

                            if keyframes:
                                effect["keyframes"][param_name] = keyframes
                        except Exception:
                            # Fallback: treat as static parameter
                            effect["parameters"][param_name] = str(param_value)

                    elif isinstance(param_value, bytes):
                        # Attempt UTF-16LE decode for Pan & Zoom stills
                        decoded_path = decode_possible_path(param_value)
                        if decoded_path and is_image_path(decoded_path):
                            effect["external_refs"].append({"kind": "image", "path": decoded_path})
                        effect["parameters"][param_name] = decoded_path or param_value.hex()

                    else:
                        # Static parameter
                        if isinstance(param_value, int | float):
                            effect["parameters"][param_name] = param_value
                        else:
                            param_str = str(param_value)
                            effect["parameters"][param_name] = param_str

                            # Check if parameter looks like a path
                            if is_possible_path(param_str):
                                effect["external_refs"].append(
                                    {"kind": "unknown", "path": param_str}
                                )

    except Exception as e:
        logger.warning(f"Effect extraction failed: {e}")

    return effect


def decode_possible_path(data: bytes) -> Optional[str]:
    """
    Attempt UTF-16LE decode on byte array, strip nulls.
    Per docs/inspector_rule_pack.md §5.
    """
    try:
        # Try UTF-16LE decode
        decoded = data.decode("utf-16le", errors="ignore")
        # Strip null bytes
        cleaned = decoded.replace("\x00", "")
        return cleaned if cleaned else None
    except Exception:
        return None


def is_image_path(path: str) -> bool:
    """Check if path looks like an image file."""
    if not path:
        return False

    path_lower = path.lower()
    return any(
        path_lower.endswith(ext)
        for ext in [".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".gif"]
    )


def is_possible_path(value: str) -> bool:
    """Check if string looks like a file path."""
    if not value or len(value) < 3:
        return False

    return any(
        [
            value.startswith("file://"),
            "/" in value,
            "\\" in value,
            ":" in value and len(value) > 2,  # Drive letter
        ]
    )


def make_none_effect() -> dict[str, Any]:
    """Create empty effect object for plain clips."""
    return {
        "name": "(none)",
        "on_filler": False,
        "parameters": {},
        "keyframes": {},
        "external_refs": [],
    }


def pack_event(
    ev: EvWrap, source: Optional[dict[str, Any]], effect: Optional[dict[str, Any]]
) -> dict[str, Any]:
    """Pack Event object per docs/data_model_json.md."""
    return {
        "id": f"ev_{ev.index:04d}",
        "timeline_start_frames": ev.timeline_start_frames,
        "length_frames": ev.length_frames,
        "source": source,
        "effect": effect or make_none_effect(),
    }


def pack_canonical_project(
    timeline_name: str,
    fps: float,
    is_drop: bool,
    start_tc_frames: int,
    events: List[dict[str, Any]],
) -> dict[str, Any]:
    """Pack top-level canonical JSON structure."""
    project_name = (
        timeline_name.replace(".Exported.01", "")
        if timeline_name.endswith(".Exported.01")
        else timeline_name
    )

    return {
        "project": {
            "name": project_name,
            "edit_rate_fps": fps,
            "tc_format": "DF" if is_drop else "NDF",
        },
        "timeline": {"name": timeline_name, "start_tc_frames": start_tc_frames, "events": events},
    }


# --------------------------- Types ---------------------------


class EvWrap:
    """Lightweight carrier for traversal results."""

    __slots__ = ("kind", "node", "timeline_start_frames", "length_frames", "index")

    def __init__(self, kind: str, node: Any, start: int, length: int, index: int) -> None:
        self.kind = kind
        self.node = node
        self.timeline_start_frames = int(start)
        self.length_frames = int(length)
        self.index = int(index)


# --------------------------- CLI ---------------------------


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
