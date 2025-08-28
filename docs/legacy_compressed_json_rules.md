Legacy Rules Derived from Compressed JSON (Top-Level CompositionMob)

Purpose: capture the exact traversal & extraction rules we proved using the compressed JSON export of the top-level CompositionMob, so they can be ported 1:1 into the new in-memory pyaaf2 parser. These rules originate from the SuperEDL/Inspector tooling and its CSV/JSON pipeline, not from direct AAF access. The function names below reference that implementation for traceability (e.g., recursive_search, find_timeline_effects, extract_effect_details, decode_filepath, etc.). These were implemented against a compressed AAF JSON structure, then enriched into SuperEDL CSV with FX details. 

Origin & Scope

Origin: Enhanced AAF Inspector → export compressed JSON of the top-level CompositionMob → analyze & reduce → Super EDL + FX CSV. The logic below reflects what worked reliably in that flow. 

Goal now: preserve these rules verbatim but bind them directly to pyaaf2 (no intermediate JSON required), producing the canonical in-memory model defined in docs/data_model_json.md.

Timeline Selection (Top-Level CompositionMob)

Choose the CompositionMob that contains the picture Sequence; when multiple exist, prefer a name ending *.Exported.01, else the first valid picture sequence. (Heuristic used in the SuperEDL scan.) 

Derive timeline edit rate (fps) from the slot’s EditRate; detect DF/NDF from the nearest Timecode.drop. Default start_tc_frames = 3600 (01:00:00:00) if no better value available. 

Traversal (Sequence → Components)

Walk Sequence.Components in order, accumulating timeline_offset in frames at the timeline rate. (recursive_search did this on the compressed tree.) 

Skip audio/data tracks; operate on picture. (“A1/A2…” guards existed in the legacy traversal.) 

Yield an Event for:

SourceClip (on-spine media).

OperationGroup without nested SourceClip (effect on filler). Detected via has_nested_source_clip() in the legacy code. 

Resulting event fields (legacy intent):

timeline_start_frames, length_frames (both ints, timeline frames).

For filler FX, source = null and an effect object is emitted. For plain clips, effect.name = "(none)". (Matches our canonical schema.)

Source Resolution (UMID Chain → Path/Metadata)

Build a mob map for fast ID→mob lookups (create_mob_map). 

For each timeline SourceClip, follow MasterMob → SourceMob → ImportDescriptor → Locator(URLString) to find the original file path (get_genuine_source_info chain logic; extract_metadata pulled URL/TapeID/DiskLabel/EditRate/Drop). Keep a umid_chain (nearest→furthest). 

Metadata precedence:

TapeID: UserComments first, else MobAttributeList.

DiskLabel: _IMPORTSETTING → TaggedValueAttributeList → _IMPORTDISKLABEL.

Source TC: use SourceMob Timecode.start @ source rate, plus IsDropFrame.

These were merged as md_master / md_final in the CSV step; we keep the same precedence. 

Do not normalize paths (keep UNC, percent-encoding, drive letters as-is). 

Effect Extraction (OperationGroup: AVX/AFX/DVE — No Filtering)

Naming: prefer _EFFECT_PLUGIN_NAME; fall back to _EFFECT_PLUGIN_CLASS; else sanitize operation label (the legacy extract_effect_details did this). 

Static parameters: capture any parameter with a direct Value (the “ADDED LOGIC to find STATIC parameters”). 

Animated parameters: capture all keyframes via PointList → ControlPoint(Time/Value) into arrays of { "t": seconds, "v": number|string }. The legacy logger printed these with computed absolute frame positions for review. 

External references: collect file-like values from parameters (strings or binary blobs that decode to paths). Tag as image/matte/unknown. 

Special: Pan & Zoom still paths

The legacy decode_filepath handled UTF-16LE byte arrays from AVX pickers, stripping nulls and cleaning slashes; find_filepath recursively searched the parameter tree. Port this detection as a decode step on bytes/list[int], and only record (don’t rewrite) when it looks like a path and extension is plausible (.jpg .png .tif …). 

Event Enrichment Heuristics (kept, but optional)

Effects that coincide with a clip and look like Pan & Zoom were treated as “override” rows with the still path surfaced.

Generic filler FX got placeholder names/paths so they remained visible in the report.

A best-effort original source length was probed from the MasterMob’s EssenceDescriptor.Length.
These were reporting conveniences in the CSV; for the canonical JSON we keep only truthful, parseable fields and avoid synthetic placeholders unless explicitly marked. 

Known Constraints of the Compressed-JSON Approach

Everything depended on the exporter’s structure (node names like "SourceClip", "Parameters", etc.). If a different exporter changed keys, parsers broke. 

Some AAF semantics (e.g., complex mob linkages, parameter typing) were flattened, so we added heuristics (e.g., UTF-16LE decode). Good for discovery, but not guaranteed robust across all AVX packages. 

Porting Rules to In-Memory pyaaf2 (What Changes/What Stays)

Stays identical (semantic rules):

What qualifies as an Event (clip vs FX-on-filler).

UMID chain resolution and metadata precedence (TapeID/DiskLabel).

Effect naming preference; static/animated parameter capture; external ref detection; Pan&Zoom UTF-16LE best-effort decode.

No path normalization.

Canonical output shape (see docs/data_model_json.md).

Changes (mechanics only):

Instead of walking a JSON list, we traverse pyaaf2 objects (CompositionMob → Slot → Sequence → Components, OperationGroup.parameters, etc.).

The Inspector’s “Test Conversion Logic” runs these same functions against live AAF objects and previews the canonical fragment (what would be produced).

JSON export becomes optional (for diagnostics/CI), not required.

See docs/inspector_rule_pack.md and docs/in_memory_pipeline.md for the live traversal contracts and builder interfaces.

Acceptance (What We Consider “Capturing the Rules”)

For any timeline with clips + AVX effects on filler, the in-memory builder recreates the same events the compressed-JSON traversal would have produced (positions, durations).

Source objects match legacy output for path, TapeID, DiskLabel, src TC/rate/drop given the same AAF.

Effect objects include all static params, all keyframes (as {t,v}), and any external refs (especially Pan&Zoom stills decoded from UTF-16LE when present).

All canonical keys exist; unknown values are null (never omitted).

Paths, UNC, percent-encoding are preserved.

Function Parallels (Traceability Map)
Legacy function (compressed JSON)	New responsibility (in-memory)
find_main_sequence_mob_and_start_tc	select_top_sequence(aaf)
recursive_search	walk_sequence_components(seq, fps)
create_mob_map	build_mob_map(aaf)
get_genuine_source_info + extract_metadata	resolve_sourceclip(sc, mob_map)
find_timeline_effects + extract_effect_details	extract_operationgroup(op)
decode_filepath / find_filepath	_coerce_value() + _decode_utf16le_best_effort()

All these live behind the canonical boundary defined in docs/data_model_json.md. The writer consumes that dict and outputs FCPXML 1.13 per docs/fcpxml_rules.md.

Why Keep This Doc

This page makes it explicit that our rules were battle-tested on a compressed JSON dump of the top-level CompositionMob (via Inspector/SuperEDL), and that the new in-memory system is a mechanical port of those rules — not a reinvention. That prevents rule drift or accidental “creative” re-interpretation when LLMs implement the parser. 

How to use this with Claude/Copilot

“Follow docs/legacy_compressed_json_rules.md for semantics; follow docs/inspector_rule_pack.md for live traversal contracts; emit the structure defined in docs/data_model_json.md.”
