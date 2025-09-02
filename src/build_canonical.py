#!/usr/bin/env python3
"""
build_canonical.py — Core AAF → Canonical JSON Implementation (KEYFRAME TIMING)

Implements the canonical JSON builder per docs/data_model_json.md and docs/inspector_rule_pack.md.
This is the primary entrypoint for converting AAF files into the canonical JSON format.

Key principles:
- Proper AAF source resolution via mob chain walking
- OperationGroup + nested SourceClip = single Media+Effect event
- Follow UMID chain to ImportDescriptor for true source info
- Required keys always present (null for unknown values)
- VERIFIED AAF keyframe timing: normalized 0.0-1.0 values per AAF Object Spec v1.1 §6.18-6.19

FIXES IMPLEMENTED:
- Stage 1: Event model corrections and deduplication
- Stage 2: True source resolution via mob chain walking  
- Stage 3: Media+Effect event pairing for ~71 event target
- Stage 4: AAF keyframe timing implementation with verified normalized model
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

from fractions import Fraction

def _to_float(x):
   try:
       if isinstance(x, (int, float)):
           return float(x)
       s = str(x)
       if "/" in s:
           n, d = s.split("/", 1)
           return float(Fraction(int(n.strip()), int(d.strip())))
       return float(s)
   except Exception:
       return None

def _classify_time_value(rational_strings):
   if not rational_strings:
       return None, None
   if len(rational_strings) == 1:
       return rational_strings[0], None
   # pick 0..1-ish as Time, other as Value
   cand = []
   for i, s in enumerate(rational_strings[:2]):
       xf = _to_float(s)
       if xf is None: 
           continue
       score = 10 if -1e-6 <= xf <= 1.05 else max(0, 1.0 - min(abs(xf), 10.0)/10.0)
       cand.append((score, i))
   cand.sort(reverse=True)
   t_idx = cand[0][1] if cand else 0
   v_idx = 1 - t_idx if len(rational_strings) > 1 else None
   t = rational_strings[t_idx]
   v = rational_strings[v_idx] if v_idx is not None else None
   return t, v

def _read_cp_props(control_point):
   edit_hint = None
   rationals = []
   tangents = {}
   try:
       for pr in control_point.properties():
           if hasattr(aaf2, 'properties') and isinstance(pr, aaf2.properties.StrongRefVectorProperty):
               # ControlPointPointProperties
               try:
                   for i in range(len(pr)):
                       item = pr.get(i)
                       iname = getattr(item, "name", None) or getattr(getattr(item, "propertydef", None), "name", None)
                       ival = None
                       for sub in item.properties():
                           sn = getattr(getattr(sub, "propertydef", None), "name", getattr(sub, "name", None))
                           if sn == "Value":
                               ival = getattr(sub, "value", None)
                               break
                       if iname:
                           tangents[str(iname)] = str(ival) if ival is not None else None
               except Exception:
                   pass
               continue
           val = getattr(pr, "value", None)
           if isinstance(val, str):
               edit_hint = val
           elif val is not None:
               rationals.append(str(val))
   except Exception:
       pass
   t_str, v_str = _classify_time_value(rationals)
   return {
       "time_str": t_str,
       "time": _to_float(t_str),
       "value_str": v_str,
       "value": _to_float(v_str),
       "edit_hint": edit_hint,
       "tangents": tangents or None,
   }

def _listify_parameters(params):
   try:
       return list(params)
   except Exception:
       out = []
       try:
           for p in params: out.append(p)
       except Exception: pass
       return out

def extract_keyframe_timing_data(operation_group):
   """
   Extract keyframes from OperationGroup using ChatGPT's proven working approach.
   Returns keyframe data or None for static parameters.
   """
   if not hasattr(operation_group, 'parameters'):
       return None
       
   # Check if any parameter is VaryingValue with multiple points
   keyframes_found = []
   
   try:
       for p in _listify_parameters(getattr(operation_group, "parameters", []) or []):
           pname = (
               getattr(getattr(p, "parameterdef", None), "name", None) or
               getattr(getattr(p, "parameter_definition", None), "name", None) or
               getattr(p, "name", "Unknown")
           )
           
           if type(p).__name__ != "VaryingValue":
               continue

           # KEY: pull PointList from the VaryingValue itself
           try:
               plist = p.get("PointList")
           except Exception:
               continue

           if not (hasattr(aaf2, 'properties') and isinstance(plist, aaf2.properties.StrongRefVectorProperty)):
               continue

           point_count = len(plist)
           if point_count <= 1:
               continue
               
           # Extract keyframes for this parameter
           param_keyframes = []
           for i in range(point_count):
               try:
                   cp = plist.get(i)
                   cp_data = _read_cp_props(cp)
                   if cp_data['time'] is not None:
                       param_keyframes.append({
                           'normalized_time': cp_data['time'],
                           'value': cp_data['value'] if cp_data['value'] is not None else 0.0,
                           'parameter_name': pname
                       })
               except Exception:
                   continue
           
           if param_keyframes:
               param_keyframes.sort(key=lambda x: x['normalized_time'])
               keyframes_found.extend(param_keyframes)
   
   except Exception as e:
       logger.debug(f"Error extracting keyframes from OperationGroup: {e}")
       return None
   
   if keyframes_found:
       return {
           'type': 'animated',
           'keyframes': keyframes_found
       }
   
   return None


def decode_avid_effect_id(byte_array):
    """Convert AvidEffectID byte array to string"""
    try:
        text = bytes(b for b in byte_array if isinstance(b, int) and b != 0).decode('ascii', errors='ignore')
        return text
    except:
        return None



def convert_normalized_time_to_fcpxml_seconds(normalized_time, segment_length_edit_units, track_edit_rate):
    """
    Convert AAF normalized keyframe time to FCPXML rational seconds.
    
    Implements verified conversion formula:
    fcpxml_seconds = (normalized_time × segment_length_edit_units) ÷ track_edit_rate
    
    Args:
        normalized_time: 0.0-1.0 value from AAF ControlPoint.Time
        segment_length_edit_units: Length of effect segment in edit units
        track_edit_rate: Track edit rate (e.g., 25.0 fps)
    
    Returns:
        float: Time in seconds for FCPXML keyframe
    """
    try:
        edit_units_position = normalized_time * segment_length_edit_units
        fcpxml_seconds = edit_units_position / track_edit_rate
        return fcpxml_seconds
    except (ZeroDivisionError, TypeError, ValueError):
        logger.warning(f"Failed to convert normalized time {normalized_time} to FCPXML seconds")
        return 0.0


def extract_fcpxml_relevant_parameters(operation_group):
    """
    Extract parameters that are relevant for FCPXML/Resolve conversion with proper keyframe timing.
    Focus on AFX/DVE parameters that have meaningful values.
    """
    if not hasattr(operation_group, 'parameters'):
        return {}
    
    # Get segment length for keyframe timing conversion
    segment_length = int(getattr(operation_group, "length", 0))
    
    try:
        extracted_params = {}
        
        for param in operation_group.parameters:
            if not (hasattr(param, 'name') and hasattr(param, 'value')):
                continue
                
            param_name = str(param.name)
            
            # Only extract parameters that matter for FCPXML conversion
            if not _is_fcpxml_relevant_parameter(param_name):
                continue
                
            # Extract the value with proper keyframe timing (25.0 fps default)
            param_data = _extract_parameter_value(param, segment_length, 25.0)
            if param_data is not None:
                extracted_params[param_name] = param_data
        
        return extracted_params
    
    except Exception as e:
        return {"extraction_error": str(e)}


def _is_fcpxml_relevant_parameter(param_name):
    """
    Determine if a parameter is relevant for FCPXML conversion.
    Focus on visual effects parameters that Resolve can use.
    """
    # AFX parameters (Avid effects that map to Resolve)
    if param_name.startswith('AFX_'):
        # Skip obvious metadata/system parameters
        if param_name in ['AFX_PARAMETER_BYTE_ORDER', 'AvidParameterByteOrder']:
            return False
        return True
    
    # DVE parameters (Digital Video Effects)
    if param_name.startswith('DVE_'):
        return True
    
    # Avid visual parameters
    visual_params = [
        'Level', 'AvidXPos', 'AvidYPos', 'AvidScale', 'AvidCrop', 
        'AvidBorderWidth', 'AvidBorderSoft', 'AvidColor'
    ]
    if param_name in visual_params:
        return True
    
    # Effect identification
    if param_name == 'AvidEffectID':
        return True
    
    return False


def _extract_parameter_value(param, segment_length_edit_units=None, track_edit_rate=25.0):
    """
    Extract parameter value, handling both animated and static cases with proper keyframe timing.
    
    Args:
        param: AAF parameter object
        segment_length_edit_units: Length of containing segment in edit units (for keyframe conversion)
        track_edit_rate: Track edit rate for time conversion
    
    Returns:
        dict: Parameter data with proper timing information
    """
    # First check for keyframe/animation data using verified timing model
    keyframe_data = extract_keyframe_timing_data(param)
    
    if keyframe_data and segment_length_edit_units is not None:
        # Convert normalized times to FCPXML seconds
        converted_keyframes = []
        
        for kf in keyframe_data["keyframes"]:
            fcpxml_seconds = convert_normalized_time_to_fcpxml_seconds(
                kf["normalized_time"], 
                segment_length_edit_units, 
                track_edit_rate
            )
            
            converted_keyframes.append({
                "time_seconds": fcpxml_seconds,
                "normalized_time": kf["normalized_time"],  # Keep for debugging
                "value": kf["value"]
            })
        
        return {
            "type": "animated",
            "keyframes": converted_keyframes
        }
    
    # Static value - use existing logic
    clean_value = _clean_parameter_value(param.value)
    if clean_value is not None:
        return {"type": "static", "value": clean_value}
    
    return None
    clean_value = _clean_parameter_value(param.value)
    if clean_value is not None:
        return {'type': 'static', 'value': clean_value}
    
    return None


def _clean_parameter_value(raw_value):
    """Clean and normalize parameter values for FCPXML use."""
    if raw_value is None:
        return None
    
    # Handle rational numbers
    if hasattr(raw_value, 'numerator') and hasattr(raw_value, 'denominator'):
        return float(raw_value)
    
    # Handle arrays/lists
    if isinstance(raw_value, (list, tuple)):
        return list(raw_value)
    
    # Handle numeric types
    if isinstance(raw_value, (int, float)):
        return float(raw_value)
    
    # Handle strings
    if isinstance(raw_value, str):
        return raw_value
    
    # Convert other types to string
    return str(raw_value)


def extract_effect_name_from_operation_group(op_group):
    """Extract effect name from OperationGroup parameters"""
    if not hasattr(op_group, 'parameters'):
        return 'Unknown Effect'
    
    try:
        params = list(op_group.parameters)
        effect_id = None
        param_prefixes = set()
        param_names = []
        
        for param in params:
            if hasattr(param, 'name') and hasattr(param, 'value'):
                name = str(param.name)
                param_names.append(name)
                
                if name == 'AvidEffectID' and isinstance(param.value, (list, tuple)):
                    effect_id = decode_avid_effect_id(param.value)
                
                if '_' in name:
                    prefix = name.split('_')[0]
                    param_prefixes.add(prefix)
        
        # Special case for Pan & Zoom
        if effect_id == 'EFF2_PAN_SCAN':
            effect_id = 'Avid Pan & Zoom'
        
        # Map to effect classes
        effect_class = 'Effect'
        if 'AFX' in param_prefixes:
            effect_class = 'AVX2 Effect'
        elif 'DVE' in param_prefixes:
            effect_class = 'Image'
        elif any(p in param_names for p in ['Level', 'AvidBorderWidth', 'AvidXPos']):
            effect_class = 'Image'
            if not effect_id:
                effect_id = 'Submaster'
        
        if effect_id:
            if effect_class and effect_class != 'Effect':
                return f'{effect_class} : {effect_id}'
            else:
                return effect_id
        else:
            return 'Unknown Effect'
    
    except Exception as e:
        logger.debug(f'Error extracting effect name: {e}')
        return 'Unknown Effect'


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

            # Step 3: Extract events using proper source resolution with deduplication
            clips, processed_operations = extract_events_with_source_resolution(comp, mob_map, fps)
            logger.info(f"Extracted {len(clips)} clips, processed {len(processed_operations)} operations")

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


def extract_events_with_source_resolution(comp_mob, mob_map: Dict[str, Any], fps: float) -> Tuple[List[Dict[str, Any]], Set[str]]:
    """
    Extract events using proper AAF source resolution.
    
    Returns:
        Tuple of (clips, processed_operations) where processed_operations tracks dedupe
    """
    clips = []
    processed_operations = set()  # STAGE 1: Deduplication tracking

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
        return clips, processed_operations

    # Process the timeline sequence
    _process_sequence(picture_slot.segment, clips, mob_map, 0, fps, processed_operations)
    return clips, processed_operations


def _process_sequence(segment, clips: List[Dict[str, Any]], mob_map: Dict[str, Any], timeline_offset: int, fps: float, processed_ops: Set[str]) -> int:
    """Process a sequence and its components."""
    if not segment or not hasattr(segment, "components"):
        return timeline_offset
    
    current_offset = timeline_offset
    components = _iter_safe(segment.components)
    
    for component in components:
        current_offset = _process_component(component, clips, mob_map, current_offset, fps, processed_ops)
    
    return current_offset


def _process_component(segment, clips: List[Dict[str, Any]], mob_map: Dict[str, Any], timeline_offset: int, fps: float, processed_ops: Set[str]) -> int:
    """Process a single timeline component."""
    if not segment:
        return timeline_offset

    segment_type = str(type(segment).__name__)
    segment_length = int(getattr(segment, "length", 0))
    
    if "OperationGroup" in segment_type:
        # STAGE 1: Each OperationGroup should produce ONE Media+Effect event with deduplication
        _process_operation_group(segment, clips, mob_map, timeline_offset, fps, processed_ops)
        
    elif "SourceClip" in segment_type:
        # Standalone SourceClip (rare in modern AAF)
        _process_source_clip(segment, clips, mob_map, timeline_offset, fps, effect_name="N/A")
        
    elif "Filler" in segment_type:
        # Pure filler - skip
        logger.debug(f"Skipping Filler at {timeline_offset}, length {segment_length}")
        
    elif "Sequence" in segment_type:
        # Nested sequence - process recursively
        return _process_sequence(segment, clips, mob_map, timeline_offset, fps, processed_ops)
    
    return timeline_offset + segment_length


def _get_operation_group_id(operation_group) -> str:
    """
    Generate a unique identifier for an OperationGroup for deduplication.
    Uses memory address as fallback if no other unique attributes available.
    """
    # Try to use operation definition as identifier
    if hasattr(operation_group, "operation_def") and operation_group.operation_def:
        op_def = operation_group.operation_def
        if hasattr(op_def, "auid"):
            return f"opgroup_{op_def.auid}"
        elif hasattr(op_def, "name"):
            return f"opgroup_{op_def.name}"
    
    # Fallback to memory address
    return f"opgroup_{id(operation_group)}"


def _process_operation_group(operation_group, clips: List[Dict[str, Any]], mob_map: Dict[str, Any], timeline_offset: int, fps: float, processed_ops: Set[str]):
    """
    Process an OperationGroup by finding its nested SourceClip and combining with effect info.
    
    STAGE 1: Implements deduplication to prevent double-emission
    STAGE 2: Extracts real effect names and performs source resolution
    STAGE 4: Implements keyframe timing extraction with verified AAF model
    """
    
    # STAGE 1: Deduplication check
    op_id = _get_operation_group_id(operation_group)
    if op_id in processed_ops:
        logger.debug(f"Skipping already processed OperationGroup: {op_id}")
        return
    processed_ops.add(op_id)
    
    # STAGE 1: Extract real effect information (not "Unknown Effect")
    operation_def = getattr(operation_group, "operation_def", None)
    effect_name = extract_effect_name_from_operation_group(operation_group)
    if operation_def:
        if hasattr(operation_def, "name") and operation_def.name:
            # Extract clean effect name
            op_name_val = str(operation_def.name)
            # Clean up common AAF operation naming patterns
            if " " in op_name_val:
                parts = op_name_val.split(" ")
                if len(parts) > 1:
                    effect_name = parts[1].replace('_v2', '').replace('_2', '').replace('_', ' ').strip()
            else:
                effect_name = op_name_val
        elif hasattr(operation_def, "auid") and operation_def.auid:
            # Use AUID as fallback
            effect_name = f"Effect_{str(operation_def.auid)[-8:]}"
    
    # STAGE 2: Find nested SourceClip via deep recursive search
    source_clip = _find_nested_source_clip_deep(operation_group)
    
    if source_clip:
        # STAGE 3: Process as Media+Effect event
        _process_source_clip(source_clip, clips, mob_map, timeline_offset, fps, effect_name, operation_group)
        logger.debug(f"Added Media+Effect event: SourceClip + {effect_name} at {timeline_offset}")
    else:
        # No SourceClip found - this is an effect on filler
        op_length = int(getattr(operation_group, "length", 0))
        filler_event = {
            "name": "Pan & Zoom on Filler" if "Avid Pan & Zoom" in effect_name else f"FX_ON_FILLER: {effect_name}",
            "in": timeline_offset,
            "out": timeline_offset + op_length,
            "source_umid": "FX_ON_FILLER",
            "source_path": None,
            "effect_params": {
                "operation": effect_name,
                "parameters": extract_fcpxml_relevant_parameters(operation_group)
            }
        }
        clips.append(filler_event)
        logger.debug(f"Added FX_ON_FILLER event: {effect_name} at {timeline_offset}")


def _find_nested_source_clip_deep(node, depth=0) -> Optional[Any]:
    """
    STAGE 1: Deep recursive search for SourceClip nested anywhere within a node.
    
    This addresses the insufficient search depth issue by traversing ALL levels:
    OperationGroup → input_segments → Sequence → components → SourceClip (and deeper)
    """
    if not node or depth > 10:  # Prevent infinite recursion
        return None
    
    node_type = str(type(node).__name__)
    
    # Found it!
    if "SourceClip" in node_type:
        return node
    
    # Skip ScopeReference - these are internal wiring, not separate events
    if "ScopeReference" in node_type:
        logger.debug(f"Skipping ScopeReference at depth {depth}")
        return None
    
    # Search all possible child containers at this depth and deeper
    search_attributes = [
        "input_segments", "segments", "inputs", "components", 
        "choices", "selected", "input_segment", "segment"
    ]
    
    for attr_name in search_attributes:
        if hasattr(node, attr_name):
            attr_value = getattr(node, attr_name)
            children = _iter_safe(attr_value)
            for child in children:
                result = _find_nested_source_clip_deep(child, depth + 1)
                if result:
                    return result
    
    return None


def _process_source_clip(source_clip, clips: List[Dict[str, Any]], mob_map: Dict[str, Any], timeline_offset: int, fps: float, effect_name: str, operation_group=None):
    """
    Process a SourceClip by walking the mob chain to resolve true source.
    
    STAGE 2: Implements true source resolution via mob chain walking
    STAGE 4: Includes keyframe parameter extraction
    """
    
    clip_length = int(getattr(source_clip, "length", 0))
    source_id = getattr(source_clip, "source_id", None)
    
    if not source_id:
        logger.warning(f"SourceClip at {timeline_offset} has no source_id")
        return
    
    # STAGE 2: Walk the mob chain to find true source
    resolved_source = walk_mob_chain_to_import_descriptor(str(source_id), mob_map)
    
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
    
    # STAGE 3: Create event combining media + effect (Media+Effect format)
    if effect_name and effect_name != "N/A":
        event_name = f"{clip_name} + {effect_name}"
    else:
        event_name = clip_name
    
    # STAGE 4: Extract keyframe parameters if operation_group provided
    parameters = {}
    if operation_group:
        parameters = extract_fcpxml_relevant_parameters(operation_group)
    
    event = {
        "name": event_name,
        "in": timeline_offset,
        "out": timeline_offset + clip_length,
        "source_umid": source_umid,
        "source_path": source_path,
        "effect_params": {
                "operation": effect_name,
                "parameters": parameters
            }
    }
    
    clips.append(event)


def walk_mob_chain_to_import_descriptor(mob_id: str, mob_map: Dict[str, Any], visited: Optional[Set[str]] = None) -> Optional[Dict[str, Any]]:
    """
    STAGE 2: Walk the mob chain following SourceIDs until reaching ImportDescriptor.
    
    This implements the core requirement: "the real source is the last mob in the resolution chain — 
    the mob with an ImportDescriptor + Locator".
    """
    if visited is None:
        visited = set()
    
    if mob_id in visited:
        logger.warning(f"Circular reference detected in mob chain: {mob_id}")
        return None
    
    visited.add(mob_id)
    mob = mob_map.get(mob_id)
    
    if not mob:
        logger.debug(f"Mob not found in map: {mob_id}")
        return None
    
    # STAGE 2: Check if this mob has an ImportDescriptor (end of chain)
    has_import_descriptor = False
    if hasattr(mob, "descriptor"):
        descriptor = mob.descriptor
        if descriptor:
            descriptor_type = str(type(descriptor).__name__)
            # Look for ImportDescriptor or similar
            if "ImportDescriptor" in descriptor_type or "NetworkLocator" in descriptor_type:
                has_import_descriptor = True
            # Also check for locators
            elif hasattr(descriptor, "locator") or (hasattr(descriptor, "locators") and _iter_safe(descriptor.locators)):
                has_import_descriptor = True
    
    if has_import_descriptor:
        # Found ImportDescriptor - extract source info
        logger.debug(f"Found ImportDescriptor at mob: {mob_id}")
        return extract_source_info_from_mob(mob)
    
    # Look for next mob in chain via SourceClip
    next_mob_id = find_next_mob_in_chain(mob)
    
    if next_mob_id and next_mob_id != mob_id:  # Avoid self-reference
        # Continue walking the chain
        result = walk_mob_chain_to_import_descriptor(next_mob_id, mob_map, visited)
        if result:
            return result
    
    # Fallback: use current mob if no chain continuation and it has descriptor info
    if hasattr(mob, "descriptor") and mob.descriptor:
        logger.debug(f"Using fallback mob for source info: {mob_id}")
        return extract_source_info_from_mob(mob)
    
    return None


def find_next_mob_in_chain(mob) -> Optional[str]:
    """Find the next MobID in the chain by looking for SourceClips in slots."""
    if not hasattr(mob, "slots"):
        return None
    
    for slot in _iter_safe(mob.slots):
        if hasattr(slot, "segment") and slot.segment:
            segment = slot.segment
            
            # Look for SourceClip in segment (may be nested)
            source_clip = _find_nested_source_clip_deep(segment)
            if source_clip:
                next_id = getattr(source_clip, "source_id", None)
                if next_id:
                    return str(next_id)
    
    return None


def extract_source_info_from_mob(mob) -> Dict[str, Any]:
    """
    STAGE 2: Extract comprehensive source information from a mob.
    
    Harvests TapeID, DiskLabel, timecode start, and path info from the authoritative source.
    """
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
    
    # STAGE 2: Extract file path from descriptor (ImportDescriptor + Locator)
    if hasattr(mob, "descriptor") and mob.descriptor:
        descriptor = mob.descriptor
        
        # Try single locator
        if hasattr(descriptor, "locator") and descriptor.locator:
            locator = descriptor.locator
            url_string = _extract_url_from_locator(locator)
            if url_string:
                source_info["source_path"] = url_string
                # Extract filename from path
                try:
                    import urllib.parse
                    parsed = urllib.parse.urlparse(url_string)
                    if parsed.path:
                        filename = os.path.basename(parsed.path)
                        if filename:
                            source_info["clip_name"] = filename
                except Exception as e:
                    logger.debug(f"Error parsing URL {url_string}: {e}")
        
        # Try multiple locators
        elif hasattr(descriptor, "locators") and descriptor.locators:
            locators = _iter_safe(descriptor.locators)
            for locator in locators:
                url_string = _extract_url_from_locator(locator)
                if url_string:
                    source_info["source_path"] = url_string
                    try:
                        import urllib.parse
                        parsed = urllib.parse.urlparse(url_string)
                        if parsed.path:
                            filename = os.path.basename(parsed.path)
                            if filename:
                                source_info["clip_name"] = filename
                    except Exception as e:
                        logger.debug(f"Error parsing URL {url_string}: {e}")
                    break  # Use first valid locator
    
    # STAGE 2: Extract TapeID and DiskLabel from attributes (as shown in legacy)
    if hasattr(mob, "attributes") and mob.attributes:
        attributes = _iter_safe(mob.attributes)
        for attr in attributes:
            if hasattr(attr, "name") and hasattr(attr, "value"):
                attr_name = str(attr.name)
                if "TapeID" in attr_name:
                    source_info["tape_id"] = str(attr.value)
                elif "DiskLabel" in attr_name or "IMPORTDISKLAB" in attr_name:
                    source_info["disk_label"] = str(attr.value)
    
    return source_info


def _extract_url_from_locator(locator) -> Optional[str]:
    """Extract URL string from a locator object."""
    if not locator:
        return None
    
    # Try common URL attributes
    url_attrs = ["url_string", "URLString", "url", "URL", "path", "Path"]
    for attr_name in url_attrs:
        if hasattr(locator, attr_name):
            url_val = getattr(locator, attr_name)
            if url_val:
                return str(url_val)
    
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


def convert_normalized_time_to_fcpxml_seconds(normalized_time, segment_length_edit_units, track_edit_rate):
    """
    Convert AAF normalized keyframe time to FCPXML rational seconds.
    
    Implements verified conversion formula:
    fcpxml_seconds = (normalized_time × segment_length_edit_units) ÷ track_edit_rate
    """
    try:
        edit_units_position = normalized_time * segment_length_edit_units
        fcpxml_seconds = edit_units_position / track_edit_rate
        return fcpxml_seconds
    except (ZeroDivisionError, TypeError, ValueError):
        logger.warning(f"Failed to convert normalized time {normalized_time} to FCPXML seconds")
        return 0.0
