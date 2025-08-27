# 🎬 AAF → Resolve Conversion Project (SuperEDL / FX)

## Goal
Build a **direct AAF → Resolve FCPXML 1.13 pipeline** (no Resolve API).  
The pipeline must:
- Use `pyaaf2==1.4.0` to parse AAF files.
- Resolve **original source clips** via UMID + SourceMobSlotID.
- Capture **every AVX/AFX/DVE effect** (OperationGroup), preserving all parameters and keyframes.
- Preserve complete metadata: TapeID, DiskLabel, edit rates, DF/NDF flags, source Timecode start, descriptor lengths.
- Produce outputs:
  1. **Canonical JSON** (source of truth, human-readable)
  2. **SQLite/DuckDB** (optional query layer)
  3. **FCPXML 1.13** (strict Resolve-compatible structure)

---

## Core Logic & Rules

### Source Resolution
- Start at the top-level **CompositionMob** (prefer name ending `.Exported.01`).
- Follow the **picture track Sequence** only.
- For each `SourceClip`, follow the **UMID chain** via MasterMob → SourceMob until reaching an `ImportDescriptor` with a `Locator(URLString)`.
- Anchor source defines:
  - File path (preserve UNC and percent-encoding)
  - TapeID: from `UserComments`, fallback to `MobAttributeList`
  - DiskLabel: `_IMPORTSETTING → TaggedValueAttributeList → _IMPORTDISKLABEL`
  - Edit rate and drop-frame/NDF
  - Genuine source Timecode start (`Timecode.start` frames)

### Timecode
- Source start TC = `Timecode.start` (frames @ source rate).
- Event start = source start frames + SourceClip offset.
- Event end = start + length.
- Timeline edit rate/DF derived from the top Sequence slot.

### Effects
- **All OperationGroups** (AVX/AFX/DVE) are included.
- Extract:
  - Effect name (`_EFFECT_PLUGIN_NAME` or `_CLASS`)
  - Parameters (static + animated keyframes)
  - Keyframes from `PointList → ControlPoint (Time/Value)`
  - External refs (stills, mattes, media paths)
- On filler:
  - If valid media path (e.g. still image) → treat as real source.
  - Else → placeholder (gap/title in FCPXML).
- **No effect ignored.**

### Metadata
- Crawl UserComments and MobAttributeList for TapeID/DiskLabel (nearest mob has precedence).
- Always preserve UNC + percent-encoded paths exactly as in the AAF.

---

## Canonical JSON Shape

```json
{
  "project": {
    "name": "Example Project",
    "edit_rate_fps": 25.0,
    "tc_format": "NDF"
  },
  "timeline": {
    "name": "ExampleTimeline.Exported.01",
    "start_tc_frames": 3600,
    "events": [
      {
        "id": "ev_0001",
        "timeline_start_frames": 0,
        "length_frames": 100,
        "source": {
          "