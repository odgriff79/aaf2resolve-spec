#!/usr/bin/env python3
"""
AAF to Canonical JSON Parser

Parses an AAF file using pyaaf2 and outputs the canonical JSON format.
See /docs/data_model_json.md for details on the data model.

Usage:
    python src/parse_aaf.py input.aaf -o output.json

Requires: pyaaf2==1.4.0, Python 3.10+
"""

import argparse
import json
import sys
import os
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple, Union

import aaf2

def aafr_to_float(rational):
    """Convert AAF Rational to float FPS."""
    if rational is None or getattr(rational, 'numerator', None) is None:
        return None
    return float(rational.numerator) / float(rational.denominator)

def build_mob_map(content):
    """Return a dict mapping mob_id (UMID) to mob."""
    mob_map = {}
    for mob in content.mobs:
        mob_id = getattr(mob, 'mob_id', None)
        if mob_id is not None:
            mob_map[str(mob_id)] = mob
    return mob_map

def harvest_usercomments(node):
    """Return dict of UserComments (MobAttributeList)."""
    uc = {}
    try:
        for tag in node['UserComments']:
            k = str(tag['Name'])
            v = tag.get('Value', None)
            uc[k] = v
    except Exception:
        pass
    return uc

def harvest_taggedvalues(node):
    """Return dict of TaggedValues (TaggedValueAttributeList)."""
    tv = {}
    try:
        for tag in node['TaggedValues']:
            k = str(tag['Name'])
            v = tag.get('Value', None)
            tv[k] = v
    except Exception:
        pass
    return tv

def decode_possible_path(value):
    """Return string path if value looks like a path; else None."""
    if not value:
        return None
    if isinstance(value, bytes):
        try:
            # Try decode as UTF-16LE, else fallback.
            s = value.decode('utf-16le', errors='ignore')
        except Exception:
            s = ""
        value = s
    if not isinstance(value, str):
        value = str(value)
    if (
        "file://" in value
        or "/" in value
        or ":\\" in value
        or value.endswith(".mov")
        or value.endswith(".mxf")
    ):
        return value.strip()
    return None

def extract_effect_name(op):
    """Extract effect name from OperationGroup attributes."""
    # Try _EFFECT_PLUGIN_NAME, then _CLASS
    try:
        for tag in getattr(op, "attributes", []):
            k = str(tag.get("Name", ""))
            if k == "_EFFECT_PLUGIN_NAME":
                return tag.get("Value", None)
            if k == "_CLASS":
                return tag.get("Value", None)
    except Exception:
        pass
    # pyaaf2 usually exposes op.operation_definition.name
    try:
        return str(op.operation_definition.name)
    except Exception:
        pass
    return None

def extract_parameters_and_keyframes(op):
    """Extract static and keyframed effect parameters."""
    params = []
    try:
        for param in op.parameters:
            name = getattr(param, 'name', None)
            value = None
            keyframes = []
            # Static value
            try:
                value = param.value
            except Exception:
                value = None
            # Keyframes
            try:
                if hasattr(param, "point_list"):
                    for pt in param.point_list:
                        kf = {"t": float(pt.time), "v": pt.value}
                        keyframes.append(kf)
            except Exception:
                pass
            params.append({
                "name": name,
                "value": value,
                "keyframes": keyframes if keyframes else None
            })
    except Exception:
        pass
    return params

def resolve_umid_chain(source_clip, mob_map):
    """
    Given a SourceClip, follow the mob chain to ImportDescriptor.
    Return dict with fields: path, umid_chain, tape_id, disk_label, src_tc_start_frames, src_rate_fps, src_drop.
    """
    result = {
        "path": None,
        "umid_chain": [],
        "tape_id": None,
        "disk_label": None,
        "src_tc_start_frames": None,
        "src_rate_fps": None,
        "src_drop": None
    }
    mob = None
    # 1. From source_clip, get source_id (UMID)
    try:
        src_ref = source_clip['SourceID']
        mob_id = str(src_ref)
    except Exception:
        mob_id = None
    visited = set()
    while mob_id and mob_id not in visited:
        visited.add(mob_id)
        mob = mob_map.get(mob_id)
        if not mob:
            break
        result["umid_chain"].append(mob_id)
        # Tape id, disk label, usercomments
        try:
            uc = harvest_usercomments(mob)
            tv = harvest_taggedvalues(mob)
            if not result["tape_id"]:
                result["tape_id"] = uc.get("TapeID") or uc.get("Tape Name")
            if not result["disk_label"]:
                result["disk_label"] = tv.get("_IMPORTDISKLABEL")
        except Exception:
            pass
        # Timecode info
        try:
            for slot in mob.slots:
                if slot.segment and slot.segment.class_name == "Timecode":
                    tc = slot.segment
                    result["src_tc_start_frames"] = getattr(tc, "start", None)
                    result["src_rate_fps"] = aafr_to_float(getattr(tc, "rate", None))
                    result["src_drop"] = tc.drop
        except Exception:
            pass
        # If ImportDescriptor found, get file path
        try:
            desc = mob.descriptor
            if desc and hasattr(desc, "locators"):
                for locator in desc.locators:
                    if hasattr(locator, "URLString"):
                        result["path"] = locator.URLString
                        break
            # Some descriptors may have path as a tagged value
            tv = harvest_taggedvalues(desc)
            if not result["path"]:
                for v in tv.values():
                    path = decode_possible_path(v)
                    if path:
                        result["path"] = path
                        break
        except Exception:
            pass
        # Next: follow source mob chain (referenced_mob)
        try:
            # For MasterMob, get its referenced SourceMob
            next_mob_id = None
            if hasattr(mob, "referenced_mobs"):
                for ref in mob.referenced_mobs():
                    next_mob_id = str(getattr(ref, "mob_id", None))
                    break
            if not next_mob_id:
                break
            mob_id = next_mob_id
        except Exception:
            break
    return result

def parse_sequence(sequence, timeline_rate, mob_map, event_list, sources, external_refs, timeline_name, track_num, timeline_start_frames):
    """
    Recursively walk Sequence components, populating event_list and sources.
    """
    for component in sequence.components:
        ctype = component.class_name
        if ctype == "Sequence":
            parse_sequence(component, timeline_rate, mob_map, event_list, sources, external_refs, timeline_name, track_num, timeline_start_frames)
        elif ctype == "SourceClip":
            source_id = str(getattr(component, "source_id", None))
            src_info = resolve_umid_chain(component, mob_map)
            # Build source entry if new
            if source_id and source_id not in sources:
                sources[source_id] = {
                    "id": source_id,
                    "name": getattr(component, "name", None),
                    "path": src_info.get("path"),
                    "rate": {
                        "numerator": int(getattr(component, "edit_rate", getattr(timeline_rate, "numerator", 24)).numerator) if getattr(component, "edit_rate", None) else int(getattr(timeline_rate, "numerator", 24)),
                        "denominator": int(getattr(component, "edit_rate", getattr(timeline_rate, "denominator", 1)).denominator) if getattr(component, "edit_rate", None) else int(getattr(timeline_rate, "denominator", 1)),
                    }
                }
            event = {
                "id": f"ev{len(event_list)+1}",
                "type": "SourceClip",
                "start": timeline_start_frames[0],
                "duration": int(getattr(component, "length", 0)),
                "track": track_num,
                "source": source_id,
                "effects": []
            }
            event_list.append(event)
            timeline_start_frames[0] += event["duration"] or 0
        elif ctype == "OperationGroup":
            name = extract_effect_name(component)
            params = extract_parameters_and_keyframes(component)
            # Check for external refs in params
            op_external_refs = []
            for p in params:
                val = p.get("value", None)
                path = decode_possible_path(val)
                if path:
                    op_external_refs.append({
                        "kind": "path" if "file://" in path else "unknown",
                        "value": path
                    })
            event = {
                "id": f"ev{len(event_list)+1}",
                "type": "OperationGroup",
                "start": timeline_start_frames[0],
                "duration": int(getattr(component, "length", 0)),
                "track": track_num,
                "source": None,
                "operation": name,
                "effects": [{
                    "id": f"fx{len(event_list)+1}",
                    "type": name,
                    "params": params
                }],
                "on_filler": all(inp.class_name == "Filler" for inp in getattr(component, "input_segments", [])) if hasattr(component, "input_segments") else None
            }
            event_list.append(event)
            timeline_start_frames[0] += event["duration"] or 0
            # Add external refs
            for ref in op_external_refs:
                external_refs.append({
                    "kind": ref["kind"],
                    "value": ref["value"]
                })
        # Other types: skip or extend as needed

def main():
    parser = argparse.ArgumentParser(description="Parse an AAF to canonical JSON")
    parser.add_argument("aaf", help="Input AAF file")
    parser.add_argument("-o", "--output", help="Output JSON file (default: stdout)")
    args = parser.parse_args()

    if not os.path.isfile(args.aaf):
        print(f"Error: File {args.aaf} not found.", file=sys.stderr)
        sys.exit(1)

    with aaf2.open(args.aaf) as f:
        mob_map = build_mob_map(f.content)
        # 1. Find CompositionMob (timeline root)
        comp_mobs = [m for m in f.content.mobs if m.class_name == "CompositionMob"]
        comp = None
        for m in comp_mobs:
            if str(getattr(m, "name", "")).endswith(".Exported.01"):
                comp = m
                break
        if comp is None and comp_mobs:
            comp = comp_mobs[0]
        if comp is None:
            print("No CompositionMob found.", file=sys.stderr)
            sys.exit(1)
        timeline_name = getattr(comp, "name", "Timeline")
        # 2. Use only the picture track (video)
        pic_slot = None
        for slot in comp.slots:
            if hasattr(slot, "segment") and getattr(slot.segment, "data_def", None) and slot.segment.data_def.name.lower().startswith("picture"):
                pic_slot = slot
                break
        if pic_slot is None:
            # fallback: first slot
            pic_slot = comp.slots[0]
        sequence = getattr(pic_slot, "segment", None)
        # 3. Timeline rate and tcFormat
        timeline_rate = getattr(pic_slot, "edit_rate", None)
        rate_num = getattr(timeline_rate, "numerator", 24)
        rate_den = getattr(timeline_rate, "denominator", 1)
        fps = aafr_to_float(timeline_rate)
        drop = None
        tc_start = 0
        try:
            for slot in comp.slots:
                if slot.segment.class_name == "Timecode":
                    tc = slot.segment
                    drop = tc.drop
                    tc_start = getattr(tc, "start", 0)
                    break
        except Exception:
            pass
        # 4. Walk sequence
        event_list = []
        sources = {}
        external_refs = []
        timeline_start_frames = [0]
        track_num = getattr(pic_slot, "slot_id", 1)
        if sequence:
            parse_sequence(
                sequence,
                timeline_rate,
                mob_map,
                event_list,
                sources,
                external_refs,
                timeline_name,
                track_num,
                timeline_start_frames
            )
        # 5. Output canonical JSON
        out_json = {
            "project": {
                "name": timeline_name,
                "rate": {
                    "numerator": int(rate_num),
                    "denominator": int(rate_den)
                },
                "timelines": [
                    {
                        "name": timeline_name,
                        "timecodeStart": int(tc_start),
                        "events": event_list,
                    }
                ],
                "sources": list(sources.values())
            }
        }
        if external_refs:
            out_json["project"]["external_refs"] = external_refs

    # Write output
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(out_json, f, indent=2, ensure_ascii=False)
    else:
        print(json.dumps(out_json, indent=2, ensure_ascii=False))

    # Print short summary
    print(f"Timeline: {timeline_name} | FPS: {fps:.3f} | Events: {len(event_list)}")

if __name__ == "__main__":
    main()