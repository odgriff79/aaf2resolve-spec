Legacy Compressed JSON Rules

These rules document how the Enhanced AAF Inspector + SuperEDL workflow operated when exporting compressed JSON from the top-level CompositionMob.

They exist for traceability: to show what worked in the legacy flow and to validate against the new in-memory pyaaf2 parser.

Origin & Scope

Origin: The Enhanced AAF Inspector exported a compressed JSON dump of the top-level CompositionMob.

That export already inlined values normally found further down the UMID chain (e.g., ImportDescriptor paths, SourceMob timecodes).

The SuperEDL/CSV logic ran against this compressed tree, applying heuristics for effects, keyframes, and still paths.

⚠️ Important: In compressed JSON, the values look comp-local, but that’s only because the exporter resolved and flattened the UMID chain before output.

Event Model

Traverse the picture Sequence of the CompositionMob.

Yield an event for each:

SourceClip → becomes a clip event.

OperationGroup on filler → becomes an effect event.

Record:

timeline_start_frames, length_frames.

source object for clips, or null for filler effects.

effect object always present ("(none)" for clips).

Source Resolution (flattened)

The compressed JSON already exposed:

source.path (resolved ImportDescriptor → Locator URL).

tape_id (UserComments/MobAttributeList).

disk_label (_IMPORTDISKLABEL).

src_tc_start_frames (SourceMob.Timecode).

src_rate_fps (slot rate).

src_drop (drop-frame flag).

No UMID traversal was needed in the JSON, because the exporter had inlined this data under the comp.

Effects

All OperationGroups were captured (no filtering).

Names from _EFFECT_PLUGIN_NAME, _EFFECT_PLUGIN_CLASS, or op label.

Parameters captured from Value fields.

Keyframes captured from PointList → ControlPoint (Time/Value).

Pan & Zoom stills were detected by heuristics:

UTF-16LE byte arrays, stripped nulls.

Checked extensions (.jpg, .png, .tif, etc.).

External refs recorded as { "kind": "image|matte|unknown", "path": "..." }.

Event Enrichment (heuristics used in CSV)

Pan & Zoom on clip: replaced path with still image path.

Filler FX: placeholder PNGs used in reports.

Original source length sometimes read from descriptor Length.

These enrichments were reporting conveniences, not canonical data.

Limitations of the Compressed JSON Approach

Depended on the exporter’s flattening logic (key names like "SourceClip", "Parameters", etc.).

If the exporter changed, parsing could break.

Some AAF semantics were lost or simplified.

Heuristics (e.g., UTF-16LE decode) worked for discovery but were not guaranteed across all AVX packages.

Porting to In-Memory Parser

Semantic rules stay the same:

Event definition (SourceClip vs OperationGroup-on-filler).

Metadata precedence (TapeID, DiskLabel).

Effect extraction (name, params, keyframes, refs).

Path fidelity (no normalization).

Mechanics change:

In direct AAF (pyaaf2), authoritative values must be read from the end of the UMID chain.

Comp-level mirrors are only used as fallback if chain resolution fails.

Legacy JSON looked self-contained only because values were already inlined.

Why Keep This Doc

It preserves the rules and heuristics that were proven to work on real productions.

It prevents accidental “rule drift” when porting to in-memory AAF traversal.

It documents the difference between compressed JSON (flattened) and direct AAF parsing (chain traversal).

Any approach that produces the same canonical JSON defined in docs/data_model_json.md is valid.

✅ With this doc, we explicitly state:

Legacy JSON was already chain-resolved.

Direct AAF must resolve UMID chain explicitly.

Both must yield the same canonical structure for downstream tools.
