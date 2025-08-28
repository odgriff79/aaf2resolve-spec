#!/usr/bin/env python3
"""
Builds the in-memory canonical dict from an AAF file.

Spec refs:
- docs/in_memory_pipeline.md
- docs/inspector_rule_pack.md
- docs/data_model_json.md
"""

from __future__ import annotations
from typing import Dict, Any, List, Tuple, Iterable, Optional
import argparse, json
import aaf2  # pyaaf2

# ---------- Helpers: types ----------

def fps_from_edit_rate(edit_rate) -> float:
    """§1.4 — derive timeline fps from slot EditRate (Rational -> float)."""
    try:
        return float(edit_rate.numerator) / float(edit_rate.denominator)
    except Exception:
        try:
            return float(edit_rate)
        except Exception:
            return 25.0

def fraction_is_drop(timecode) -> bool:
    """§1.5 — derive DF/NDF from Timecode.drop."""
    try:
        return bool(getattr(timecode, "drop", False))
    except Exception:
        return False

# ---------- Selection ----------

def select_top_sequence(aaf) -> Tuple[Any, float, bool, int, str]:
    """
    §1.1–1.5 Pick top-level CompositionMob (prefer *.Exported.01), picture track only.
    Returns: (seq, fps, drop, start_tc_frames, timeline_name)
    """
    header = aaf.content
    comps = [m for m in header.mobs if m.class_name == "CompositionMob"]
    # prefer *.Exported.01
    comp = next((m for m in comps if str(m.name or "").endswith(".Exported.01")), comps[0])
    # picture slot (usually slot id 1)
    picture_slot = next(s for s in comp.slots if getattr(s, "segment", None) and getattr(s, "slot_id", 0) >= 0)
    seq = picture_slot.segment  # Sequence or SourceClip/OpGroup if trivial
    fps = fps_from_edit_rate(picture_slot.edit_rate)
    # find nearest timeline timecode if present
    start_tc_frames = 3600  # default to 01:00:00:00 @ fps, per rules
    drop = False
    try:
        # look for a Timecode segment to detect drop/non-drop
        if hasattr(seq, "components"):
            for c in seq.components:
                if c.class_name == "Timecode":
                    drop = fraction_is_drop(c)
                    break
    except Exception:
        pass
    return seq, fps, drop, start_tc_frames, (comp.name or "Timeline")

# ---------- Traversal ----------

class EvWrap:
    __slots__ = ("kind", "node", "timeline_start_frames", "length_frames", "index")
    def __init__(self, kind, node, start, length, index):
        self.kind = kind
        self.node = node
        self.timeline_start_frames = int(start)
        self.length_frames = int(length)
        self.index = index

def walk_sequence_components(seq, fps: float) -> Iterable[EvWrap]:
    """
    §1.2–1.6 Walk the picture sequence, yielding SourceClip events and
    OperationGroup-on-filler events. Recurse nested Sequences.
    """
    def _walk(seg, start, idx):
        # If it's a Sequence, iterate components
        if hasattr(seg, "components"):
            for comp in seg.components:
                length = int(getattr(comp, "length", 0))
                # classify
                cls = comp.class_name
                if cls == "SourceClip":
                    yield EvWrap("sourceclip", comp, start, length, idx); idx += 1
                elif cls == "OperationGroup":
                    # treat as on-filler unless it clearly references a SourceClip input
                    yield EvWrap("operationgroup_on_filler", comp, start, length, idx); idx += 1
                elif cls == "Sequence":
                    for ev in _walk(comp, start, idx):
                        yield ev
                        idx = ev.index + 1
                # advance timeline
                start += length
        else:
            length = int(getattr(seg, "length", 0))
            yield EvWrap("unknown", seg, start, length, idx)
        return
    return _walk(seq, 0, 1)

# ---------- Mob map + source resolution ----------

def build_mob_map(aaf) -> Dict[str, Any]:
    """Map of mob id (string UMID) → mob, for fast lookups. §3"""
    m = {}
    for mob in aaf.content.mobs:
        try:
            m[str(mob.mob_id)] = mob
        except Exception:
            pass
    return m

def resolve_sourceclip(sc, mob_map) -> Dict[str, Any]:
    """
    §3 Follow UMID chain MasterMob→SourceMob→ImportDescriptor→Locator(URLString).
    Also gather TapeID, DiskLabel, src timecode/rate/drop.
    """
    umids: List[str] = []
    path = None
    tape_id = None
    disk_label = None
    src_tc_start_frames = None
    src_rate_fps = None
    src_drop = False

    try:
        src_id = str(sc.source_id)
        umids.append(src_id)
        mob = mob_map.get(src_id)
        visited = set()
        while mob and str(mob.mob_id) not in visited:
            visited.add(str(mob.mob_id))
            # ImportDescriptor?
            try:
                desc = getattr(mob, "descriptor", None)
                if desc and hasattr(desc, "locators") and desc.locators:
                    for loc in desc.locators:
                        # URLString or similar
                        if hasattr(loc, "url_string"):
                            path = loc.url_string
                            break
                # metadata: TapeID from UserComments or MobAttributeList
                tape_id = tape_id or _harvest_tape_id(mob)
                disk_label = disk_label or _harvest_disk_label(mob)
            except Exception:
                pass
            # timecode + rate
            try:
                # source edit rate
                for s in mob.slots:
                    if getattr(s, "segment", None) and s.segment.class_name == "Timecode":
                        tc = s.segment
                        src_tc_start_frames = int(getattr(tc, "start", src_tc_start_frames or 0))
                        src_drop = fraction_is_drop(tc)
                    if getattr(s, "edit_rate", None):
                        src_rate_fps = src_rate_fps or fps_from_edit_rate(s.edit_rate)
            except Exception:
                pass
            # follow next reference via essence mobs if present
            next_id = _next_umid_from_mob(mob)
            if next_id and next_id not in visited:
                umids.append(next_id)
                mob = mob_map.get(next_id)
            else:
                break
    except Exception:
        pass

    return {
        "path": path,
        "umid_chain": umids,
        "tape_id": tape_id,
        "disk_label": disk_label,
        "src_tc_start_frames": src_tc_start_frames,
        "src_rate_fps": src_rate_fps or 25.0,
        "src_drop": bool(src_drop),
    }

def _harvest_tape_id(mob) -> Optional[str]:
    # §3.4 precedence: UserComments → MobAttributeList
    try:
        for tv in getattr(mob, "user_comments", []) or []:
            if (getattr(tv, "name", "") or "").lower() in ("tape", "tapeid", "tape_id"):
                return tv.value
    except Exception:
        pass
    try:
        for tv in getattr(mob, "attributes", []) or []:
            if (getattr(tv, "name", "") or "").lower() in ("tape", "tapeid", "tape_id"):
                return tv.value
    except Exception:
        pass
    return None

def _harvest_disk_label(mob) -> Optional[str]:
    # §3.4 disk_label via _IMPORTSETTING → TaggedValueAttributeList → _IMPORTDISKLABEL
    try:
        for tv in getattr(mob, "attributes", []) or []:
            name = getattr(tv, "name", "")
            if name == "_IMPORTDISKLABEL":
                return tv.value
    except Exception:
        pass
    return None

def _next_umid_from_mob(mob) -> Optional[str]:
    """Best-effort hop to the next mob in the chain."""
    try:
        # Typical AAF: mob has source_refs; take first
        for slot in mob.slots:
            seg = getattr(slot, "segment", None)
            if seg and hasattr(seg, "components"):
                for c in seg.components:
                    if c.class_name == "SourceClip":
                        return str(getattr(c, "source_id", "") or "")
    except Exception:
        pass
    return None

# ---------- Effects ----------

def extract_operationgroup(op) -> Dict[str, Any]:
    """§4–5 Any AVX/AFX/DVE: name, on_filler, parameters, keyframes, external_refs."""
    name = _effect_name(op)
    params: Dict[str, Any] = {}
    kfs: Dict[str, List[Dict[str, Any]]] = {}
    refs: List[Dict[str, str]] = []

    # iterate parameters
    try:
        for par in getattr(op, "parameters", []) or []:
            p_name = getattr(par, "name", None) or getattr(par, "parameter_name", "Param")
            # static value?
            if hasattr(par, "value"):
                val = par.value
                params[p_name] = _coerce_value(val, refs)
            # keyframes?
            plist = getattr(par, "point_list", None) or getattr(par, "pointlist", None)
            if plist:
                series = []
                for cp in getattr(plist, "control_points", []) or []:
                    t = float(getattr(cp, "time", 0.0))
                    v = _coerce_value(getattr(cp, "value", None), refs)
                    series.append({"t": t, "v": v})
                if series:
                    kfs[p_name] = series
    except Exception:
        pass

    return {
        "name": name or "(unknown)",
        "on_filler": True,  # builder sets True for OpGroup yielded as 'operationgroup_on_filler'
        "parameters": params,
        "keyframes": kfs,
        "external_refs": refs,
    }

def _effect_name(op) -> str:
    # §4: prefer _EFFECT_PLUGIN_NAME / _EFFECT_PLUGIN_CLASS
    try:
        attrs = getattr(op, "attributes", []) or []
        byname = {getattr(a, "name", ""): getattr(a, "value", "") for a in attrs}
        return byname.get("_EFFECT_PLUGIN_NAME") or byname.get("_EFFECT_PLUGIN_CLASS") or (op.operation or "").strip()
    except Exception:
        return (getattr(op, "operation", "") or "").strip() or "(none)"

def _coerce_value(v, refs: List[Dict[str, str]]):
    """Detect path-like values (including UTF-16LE-ish byte lists) and record in external_refs."""
    if v is None:
        return None
    # strings
    if isinstance(v, str):
        if _looks_like_path(v):
            refs.append({"kind": _guess_kind(v), "path": v})
        return v
    # numbers
    try:
        return float(v) if isinstance(v, (int, float)) else v
    except Exception:
        pass
    # byte arrays / lists (Pan&Zoom)
    try:
        if isinstance(v, (bytes, bytearray)):
            s = _decode_utf16le_best_effort(bytes(v))
            if s and _looks_like_path(s):
                refs.append({"kind": _guess_kind(s), "path": s})
            return s or repr(v)
        if isinstance(v, list) and all(isinstance(x, int) for x in v):
            b = bytes(v)
            s = _decode_utf16le_best_effort(b)
            if s and _looks_like_path(s):
                refs.append({"kind": _guess_kind(s), "path": s})
            return s or repr(v)
    except Exception:
        return repr(v)
    return v

def _decode_utf16le_best_effort(b: bytes) -> Optional[str]:
    try:
        s = b.decode("utf-16le", errors="ignore").replace("\x00", "")
        return s.strip() or None
    except Exception:
        return None

def _looks_like_path(s: str) -> bool:
    s_l = s.lower()
    return ("file://" in s_l) or (":\\" in s) or ("/" in s)

def _guess_kind(s: str) -> str:
    for ext in (".jpg",".jpeg",".png",".tif",".tiff",".bmp",".gif"):
        if s.lower().endswith(ext):
            return "image"
    return "unknown"

# ---------- Packing ----------

def pack_event(ev: EvWrap, source: Optional[Dict[str, Any]], effect: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "id": f"ev_{ev.index:04d}",
        "timeline_start_frames": ev.timeline_start_frames,
        "length_frames": ev.length_frames,
        "source": source,
        "effect": effect or {"name": "(none)", "on_filler": False, "parameters": {}, "keyframes": {}, "external_refs": []},
    }

def pack_canonical_project(timeline_name: str, fps: float, drop: bool, start_frames: int, events: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "project": {
            "name": timeline_name,
            "edit_rate_fps": float(fps),
            "tc_format": "DF" if drop else "NDF"
        },
        "timeline": {
            "name": timeline_name,
            "start_tc_frames": int(start_frames),
            "events": events
        }
    }

# ---------- Top-level ----------

def build_canonical_from_aaf(path: str) -> Dict[str, Any]:
    with aaf2.open(path, "r") as aaf:
        seq, fps, drop, start_frames, name = select_top_sequence(aaf)
        mob_map = build_mob_map(aaf)
        events: List[Dict[str, Any]] = []
        for ev in walk_sequence_components(seq, fps):
            if ev.kind == "sourceclip":
                src = resolve_sourceclip(ev.node, mob_map)
                effect = {"name": "(none)", "on_filler": False, "parameters": {}, "keyframes": {}, "external_refs": []}
                events.append(pack_event(ev, src, effect))
            elif ev.kind == "operationgroup_on_filler":
                fx = extract_operationgroup(ev.node)
                fx["on_filler"] = True
                events.append(pack_event(ev, None, fx))
        return pack_canonical_project(name, fps, drop, start_frames, events)

def main():
    ap = argparse.ArgumentParser(description="Build in-memory canonical dict from AAF and print/save JSON.")
    ap.add_argument("aaf", help="Path to AAF file")
    ap.add_argument("-o", "--out", default="-", help="Output JSON path (default stdout)")
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
