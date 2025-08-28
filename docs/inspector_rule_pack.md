
---

## 3) Create `docs/inspector_rule_pack.md`
Paste this whole file:

```markdown
# Inspector Rule Pack (Traversal, UMID Resolution, Effect Extraction)

These are the deterministic rules the in-memory builder and the Enhanced AAF Inspector must follow. They are derived from prior SuperEDL/GUI logic and formalized here.

## 1) Timeline selection & traversal
1. Pick **top-level CompositionMob** with name ending `.Exported.01`; else the first CompositionMob.
2. Use **picture** Sequence track only; skip audio/data.
3. Walk `Sequence.Components` in order; maintain `timeline_offset` (frames).
4. Derive **timeline fps** from the picture slot’s `EditRate`.
5. Set project `tc_format` from the nearest `Timecode.drop` (`"DF"` vs `"NDF"`).
6. Each traversed component yields an **Event** when:
   - It’s a `SourceClip`, or
   - It’s an `OperationGroup` on filler (no SourceClip input).

## 2) Event packing (shared structure)
For each event:
- `id` = stable index (`ev_0001` …)
- `timeline_start_frames` = current offset (int)
- `length_frames` = component length (int)
- `source`:
  - Present for clips (object).
  - `null` for effects on filler.
- `effect`:
  - Always present.
  - `"(none)"` for plain clips without an effect.

## 3) Source resolution (UMID chain → Locator(URLString))
From a `SourceClip`:
1. Follow **SourceID/UMID** through MasterMob → SourceMob until reaching an **ImportDescriptor**.
2. Find **Locator(URLString)**; set `source.path` to the exact URI/UNC (preserve encoding).
3. Build `source.umid_chain` (nearest → furthest).
4. Tape/Disk precedence (nearest win):
   - `tape_id`: `UserComments` → `MobAttributeList`.
   - `disk_label`: `_IMPORTSETTING → TaggedValueAttributeList → _IMPORTDISKLABEL`.
5. Source timecode:
   - `src_tc_start_frames` = SourceMob `Timecode.start` (frames @ source rate).
   - `src_rate_fps` from SourceMob or slot edit rate; `src_drop` from drop flag.

## 4) Effects (OperationGroup: AVX/AFX/DVE — no filtering)
- **Name**: prefer `_EFFECT_PLUGIN_NAME`, then `_EFFECT_PLUGIN_CLASS`, else operation label.
- **on_filler**: `true` if all inputs are non-SourceClip (pure effect on filler).
- **parameters**:
  - For each parameter with a `Value`, store as number/string.
- **keyframes**:
  - For `PointList → ControlPoint`: convert `Time/Value` to `{ "t": <seconds>, "v": <number|string> }`.
- **external_refs**:
  - If a parameter value is a probable path (string with `file://`, `/`, `:\` or byte/UTF-16LE list), append `{ "kind": "image|matte|unknown", "path": "..." }`.

## 5) Pan & Zoom stills (path decoding)
- Try **UTF-16LE** decode on AVX blobs.
- Strip nulls; preserve drive letters and UNC.
- Validate extensions against common image types (`.jpg`, `.jpeg`, `.png`, `.tif`, `.tiff`, `.bmp`, `.gif`).
- Keep the **original string** if decoding fails; don’t “fix” the path.

## 6) Nullability & precedence
- Always include required keys; use `null` when unknown.
- Nearest valid metadata wins (Import/Source mobs over Master).
- Do not normalize or rewrite paths.

## Inspector hooks (UX)
- Right-click a node:
  - **Resolve Source Chain** → shows the `source` object that would be packed.
  - **Extract Effect** → shows the `effect` object (name, parameters, keyframes, external_refs).
  - **Decode Possible Path** → shows raw vs decoded forms; marks best guess.
  - **Preview Canonical Fragment** → shows the JSON fragment per `docs/data_model_json.md`.
- **Build Canonical Timeline** → runs the full traversal and displays the full canonical JSON (optional save to file).

## Acceptance checks
- On a timeline with mixed clips and AVX effects on filler:
  - Events appear in order with correct `timeline_start_frames` and `length_frames`.
  - Source clips have a resolved `path` or `null` if no Locator(URLString).
  - Effects always present; `on_filler` correctly set; parameters and keyframes captured.
  - External stills detected for Pan&Zoom-like AVX payloads when present.
