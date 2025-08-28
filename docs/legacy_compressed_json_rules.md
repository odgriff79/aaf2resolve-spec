Legacy Rules Derived from Compressed JSON (Top-Level CompositionMob)

⚠️ Important:
This document records one proven method (via compressed JSON dump of the top-level CompositionMob, produced by Enhanced AAF Inspector → SuperEDL).
It shows traversal & extraction rules that worked in practice and must be preserved semantically.

✅ However, this is not the only acceptable method.
Any approach that can:

Explore a top-level CompositionMob directly in an AAF,

Derive equivalent events, source metadata, and effects, and

Produce the canonical JSON structure defined in docs/data_model_json.md

…is equally valid. This doc exists for traceability and proven semantics, not to lock us into one path.

Purpose

Capture the exact traversal & extraction rules we proved using the compressed JSON export of the top-level CompositionMob, so they can be ported 1:1 into the new in-memory pyaaf2 parser.

These rules originated from the SuperEDL/Inspector tooling and its CSV/JSON pipeline, not from direct AAF access. Function names below reference that implementation for traceability (recursive_search, find_timeline_effects, extract_effect_details, decode_filepath, etc.).

Origin & Scope

Origin: Enhanced AAF Inspector → export compressed JSON of the top-level CompositionMob → analyze & reduce → SuperEDL + FX CSV.

Goal now: preserve these rules verbatim but bind them directly to pyaaf2 (no intermediate JSON required), producing the canonical in-memory model defined in docs/data_model_json.md
.

Scope: Timeline traversal, UMID resolution, metadata precedence, effect extraction, and event packaging.

Timeline Selection (Top-Level CompositionMob)

Choose the CompositionMob that contains the picture Sequence; when multiple exist, prefer a name ending *.Exported.01, else the first valid picture sequence.

Derive timeline edit rate (fps) from the slot’s EditRate; detect DF/NDF from the nearest Timecode.drop.

Default start_tc_frames = 3600 (01:00:00:00) if no better value is available.

Traversal (Sequence → Components)

Walk Sequence.Components in order, accumulating timeline_offset in frames at the timeline rate.

Skip audio/data tracks; operate on picture only.

Yield an Event for:

SourceClip (on-spine media).

OperationGroup without nested SourceClip (effect on filler).

Resulting event fields:

timeline_start_frames, length_frames (both ints).

For filler FX, source = null and an effect object is emitted.

For plain clips, effect.name = "(none)".

Source Resolution (UMID Chain → Path/Metadata)

Build a mob map for fast ID→mob lookups (create_mob_map).

For each timeline SourceClip, follow MasterMob → SourceMob → ImportDescriptor → Locator(URLString) to find the original file path.

Keep a umid_chain (nearest→furthest).

Metadata precedence:

TapeID: UserComments first, else MobAttributeList.

DiskLabel: _IMPORTSETTING → TaggedValueAttributeList → _IMPORTDISKLABEL.

Source TC: use SourceMob Timecode.start @ source rate, plus IsDropFrame.

Do not normalize paths (keep UNC, percent-encoding, drive letters as-is).

Effect Extraction (OperationGroup: AVX/AFX/DVE — No Filtering)

Naming: prefer _EFFECT_PLUGIN_NAME; fall back to _EFFECT_PLUGIN_CLASS; else sanitize operation label.

Static parameters: capture any parameter with a direct Value.

Animated parameters: capture all keyframes via PointList → ControlPoint(Time/Value) into arrays of { "t": seconds, "v": number|string }.

External references: collect file-like values from parameters (strings or binary blobs that decode to paths). Tag as image|matte|unknown.

Special: Pan & Zoom still paths

Handle UTF-16LE byte arrays from AVX pickers (decode_filepath).

Strip nulls, preserve drive letters/UNC.

Validate extensions (.jpg .png .tif …).

Only record the string if plausible; do not rewrite/normalize.

Event Enrichment Heuristics (Optional)

Effects coinciding with a clip and resembling Pan & Zoom were treated as “override” rows with the still path surfaced.

Generic filler FX got placeholder names/paths so they remained visible in reports.

A best-effort original source length was probed from the MasterMob’s EssenceDescriptor.Length.

➡️ In the canonical JSON, we keep only truthful, parseable fields, and avoid synthetic placeholders unless explicitly marked.

Known Constraints of the Compressed-JSON Approach

Depended on the exporter’s structure (node names like "SourceClip", "Parameters"). A change in exporter could break parsing.

Some AAF semantics (complex mob linkages, parameter typing) were flattened, requiring heuristics (e.g., UTF-16LE decode).

Good for discovery, but not guaranteed across all AVX packages.

Porting Rules to In-Memory pyaaf2

Stays identical (semantic rules):

What qualifies as an Event.

UMID chain resolution and metadata precedence (TapeID/DiskLabel).

Effect naming preference.

Static/animated parameter capture.

External ref detection (including Pan&Zoom UTF-16LE decode).

No path normalization.

Canonical output shape (docs/data_model_json.md).

Changes (mechanics only):

Traverse pyaaf2 objects instead of JSON trees.

Inspector hooks can test these functions live on AAFs.

JSON export is now optional (diagnostics/CI only).

Acceptance (Capturing the Rules)

Events appear in the same order, with correct timeline_start_frames and length_frames.

Source objects match legacy output for path, TapeID, DiskLabel, source TC/rate/drop.

Effect objects include all static params, all keyframes, and any external refs (e.g. Pan&Zoom stills).

All canonical keys exist; unknown values = null.

Paths, UNC, percent-encoding are preserved.

Function Parallels (Traceability Map)
Legacy function (compressed JSON)	In-memory replacement
find_main_sequence_mob_and_start_tc	select_top_sequence(aaf)
recursive_search	walk_sequence_components(seq, fps)
create_mob_map	build_mob_map(aaf)
get_genuine_source_info + extract_metadata	resolve_sourceclip(sc, mob_map)
find_timeline_effects + extract_effect_details	extract_operationgroup(op)
decode_filepath / find_filepath	_coerce_value() + _decode_utf16le_best_effort()
Why Keep This Doc

Makes it explicit that our rules were battle-tested on compressed JSON of the top-level CompositionMob.

Ensures the in-memory system is a mechanical port of those semantics, not a reinvention.

Prevents accidental “creative” reinterpretation by LLMs.

How to Use This with Claude/Copilot

Follow docs/legacy_compressed_json_rules.md for semantics.
Follow docs/inspector_rule_pack.md for live traversal contracts.
Emit the structure defined in docs/data_model_json.md.

✅ This merged version preserves all detail and makes clear that any working approach is valid as long as it reaches the same canonical structure.
