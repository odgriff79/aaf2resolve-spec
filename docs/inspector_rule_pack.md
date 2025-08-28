Inspector Rule Pack (Traversal, UMID Resolution, Effect Extraction)

These are the deterministic rules the in-memory builder and the Enhanced AAF Inspector must follow. They are derived from prior SuperEDL/Inspector logic and formalized here.

1) Timeline selection & traversal

Pick top-level CompositionMob with name ending .Exported.01; else the first CompositionMob.

Use picture Sequence track only; skip audio/data.

Walk Sequence.Components in order; maintain timeline_offset (frames).

Derive timeline fps from the picture slot’s EditRate.

Set project tc_format from the nearest Timecode.drop ("DF" vs "NDF").

Each traversed component yields an Event when:

It’s a SourceClip, or

It’s an OperationGroup on filler (no SourceClip input).

2) Event packing (shared structure)

For each event:

id = stable index (ev_0001, ev_0002 …)

timeline_start_frames = current offset (int)

length_frames = component length (int)

source:

Present for clips (object).

null for effects on filler.

effect:

Always present.

"(none)" for plain clips without an effect.

3) Source resolution (authoritative-first)

For each SourceClip:

Follow the UMID chain: SourceClip → MasterMob → SourceMob → ImportDescriptor.

At the chain end:

Path: from ImportDescriptor → Locator(URLString).

TapeID: from UserComments, else MobAttributeList (nearest wins).

DiskLabel: from _IMPORTSETTING → TaggedValueAttributeList → _IMPORTDISKLABEL.

Source timecode: from SourceMob.Timecode.start (frames @ source rate).

Source rate: from SourceMob or slot edit rate.

Drop flag: from SourceMob.Timecode.drop.

Build source.umid_chain (nearest → furthest).

Fallback rule:

If the chain is broken (no Locator, missing mobs), use any comp-level mirrors that exist.

Set missing values to null.

Never abort; emit the event even if partially populated.

Preserve fidelity: Do not normalize paths. Keep UNC, percent-encoding, drive letters, and slashes exactly as found.

4) Effects (OperationGroup: AVX/AFX/DVE — no filtering)

Name: prefer _EFFECT_PLUGIN_NAME, then _EFFECT_PLUGIN_CLASS, else operation label.

on_filler: true if all inputs are non-SourceClip (pure filler effect).

parameters:

For each parameter with a Value, store as number/string.

keyframes:

For PointList → ControlPoint: convert Time/Value to
{ "t": <seconds>, "v": <number|string> }.

external_refs:

If a parameter looks like a path (string with file://, /, :\ or byte/UTF-16LE array), append
{ "kind": "image|matte|unknown", "path": "..." }.

5) Pan & Zoom stills (path decoding)

Attempt UTF-16LE decode on AVX parameter blobs.

Strip nulls; preserve drive letters and UNC.

Validate extensions against common image formats (.jpg, .jpeg, .png, .tif, .tiff, .bmp, .gif).

If decoding fails, keep the original raw string. Never rewrite.

6) Nullability & precedence

Always include required keys; use null when unknown.

Within the UMID chain, nearest valid metadata wins.

Comp-level values are fallback only if the chain is broken.

Do not normalize or rewrite paths.

Inspector hooks (UX)

Right-click a node:

Resolve Source Chain → shows the source object that would be packed.

Extract Effect → shows the effect object (name, parameters, keyframes, external_refs).

Decode Possible Path → shows raw vs decoded forms; marks best guess.

Preview Canonical Fragment → shows JSON fragment per docs/data_model_json.md.

Build Canonical Timeline → runs the full traversal and displays canonical JSON (optional save to file).

Acceptance checks

On a timeline with clips + AVX effects on filler:

Events appear in playback order with correct timeline_start_frames and length_frames.

Source clips resolve authoritative metadata at chain end (path, TapeID, DiskLabel, timecode, fps/drop).

If chain resolution fails, comp-level fallback is allowed (path may be null).

Effects always present; on_filler correctly set; parameters and keyframes captured.

External stills detected for Pan&Zoom-like AVX payloads when present.

✅ This version fixes the earlier ambiguity:

Direct AAF parsing: authoritative chain-end values are always primary.

Comp-level values: fallback only if the chain is broken.

Legacy compressed JSON: was already chain-resolved, which is why it looked comp-local.
