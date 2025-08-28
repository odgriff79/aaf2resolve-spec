# In-Memory Canonical Pipeline (AAF → Canonical → FCPXML)

This document defines the **direct** AAF reading approach (no required intermediate files) while preserving the same canonical structure used across this project.

## Goals
- Read AAF via `pyaaf2` directly, build the **canonical model in RAM**.
- Use the **Enhanced AAF Inspector** for interactive debugging (probe any node; preview canonical fragments).
- Keep JSON export **optional** (for diagnostics/CI), not required for the main flow.
- Feed the canonical dict straight to the **FCPXML writer**.

## Canonical boundary (contract)
The in-memory dict **must exactly match** the schema in `docs/data_model_json.md`. Writers read this dict (or its JSON dump).

## Architecture

### Layer A — Inspector runtime
- Qt tree viewer over `pyaaf2` objects.
- Context menu actions to:
  - “Resolve Source Chain”
  - “Extract Effect Params/Keyframes”
  - “Decode Possible Path (UTF-16LE, URL, bytes)”
  - “Preview Canonical Fragment”
- Button: “Build Canonical Timeline” → renders pretty JSON panel (and **optionally** saves JSON).

### Layer B — Canonical builder
- Pure functions that:
  1) Select top CompositionMob (prefer `*.Exported.01`)
  2) Walk picture Sequence components in order (recurse nested Sequence)
  3) Resolve `SourceClip` via UMID chain → ImportDescriptor → Locator(URLString)
  4) Extract **all** OperationGroup parameters + keyframes + external refs
  5) Pack events and top-level fields per the schema

## Suggested interfaces

```python
# src/build_canonical.py
from typing import Dict, Any
import aaf2

def build_canonical_from_aaf(path: str) -> Dict[str, Any]:
    """Open AAF, build canonical dict per docs/data_model_json.md."""
    with aaf2.open(path, 'r') as f:
        comp, fps, drop, start_frames = select_top_sequence(f)
        mob_map = build_mob_map(f)
        events = []
        for ev in walk_sequence_components(comp, fps):  # yields typed wrappers with .kind, .node, .length_frames, .timeline_start_frames
            if ev.kind == "sourceclip":
                src = resolve_sourceclip(ev.node, mob_map)
                fx = extract_inline_effect_if_any(ev.node)  # optional
                events.append(pack_event(ev, src, fx))
            elif ev.kind == "operationgroup_on_filler":
                fx = extract_operationgroup(ev.node)
                events.append(pack_event(ev, None, fx))
        return pack_canonical_project(comp, fps, drop, start_frames, events)
