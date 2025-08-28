Canonical JSON Data Model

This document defines the single source of truth JSON emitted by the AAF parser and consumed by the FCPXML writer (and optionally loaded into SQLite). It is schema-first, human-readable, git-diffable, and designed for lossless capture of AAF timeline semantics.

Golden rule: Writers read JSON, not the DB. The DB is optional for querying/analytics.

Top-level structure
{
  "project": { ... },
  "timeline": { ... }
}

Types used

int — whole frames, counts, indices

float — fps values, seconds for keyframes

string — names, paths, UMIDs

bool — true/false

null — unknown/unavailable

Field-by-field specification
project (object)
Field	Type	Req	Description
name	string	✓	Usually derived from the AAF filename (without extension).
edit_rate_fps	float	✓	Timeline frame rate (e.g., 25.0, 23.976).
tc_format	string	✓	"DF" or "NDF" for drop/non-drop at the sequence level.
timeline (object)
Field	Type	Req	Description
name	string	✓	Name of the top-level CompositionMob (prefer *.Exported.01).
start_tc_frames	int	✓	Starting timecode in frames (e.g., 3600 for 01:00:00:00 @ 25fps).
events	array<Event>	✓	Flattened list of timeline components in playback order.
Event (object)

Each entry in timeline.events represents either a SourceClip or an OperationGroup (any AVX/AFX/DVE effect). No effect is ignored.

Field	Type	Req	Description
id	string	✓	Stable event id (e.g., ev_0001).
timeline_start_frames	int	✓	Absolute timeline offset for this event (in frames).
length_frames	int	✓	Event duration (in frames).
source	object | null	✓	Present for clips; null for pure effects on filler. See Source.
effect	object	✓	Always present; "(none)" for plain clips. See Effect.
Source (object)

Describes original media resolved via the UMID chain (to ImportDescriptor → Locator(URLString)).

Field	Type	Req	Description
path	string | null	✓	Original media URI/UNC path. Preserve percent-encoding and UNC exactly.
umid_chain	array<string>	✓	String UMIDs traversed during resolution (nearest → furthest).
tape_id	string | null	✓	From UserComments first, else MobAttributeList.
disk_label	string | null	✓	From _IMPORTSETTING → TaggedValueAttributeList → _IMPORTDISKLABEL.
src_tc_start_frames	int | null	✓	SourceMob Timecode.start (frames @ source rate).
src_rate_fps	float	✓	Source frame rate (from SourceMob or slot edit rate).
src_drop	bool	✓	Drop-frame flag for the source timecode.
Effect (object)

Represents any OperationGroup (AVX/AFX/DVE). For plain clips, name="(none)", on_filler=false, empty params.

Field	Type	Req	Description
name	string	✓	Plugin/effect label (from _EFFECT_PLUGIN_NAME/_CLASS if present).
on_filler	bool	✓	true if the effect sits on filler (no clip input).
parameters	object	✓	Map of static parameter values (numbers/strings).
keyframes	object	✓	Map: param → array of objects `{ "t": <float seconds>, "v": <number
external_refs	array<ExternalRef>	✓	File references discovered in parameters (stills, mattes, etc.).

ExternalRef (object)

Field	Type	Req	Description
kind	string	✓	"image", "matte", or "unknown" (best guess).
path	string	✓	Path/URI as found (preserve original).
Conventions
Timing

Frames: timeline_start_frames, length_frames, start_tc_frames, src_tc_start_frames.

Seconds: keyframe t (float seconds from the start of the event).

Rates: edit_rate_fps, src_rate_fps are floats (use 23.976, 29.97, 59.94 where applicable).

Paths

Preserve UNC (e.g., //RadiantNexis00/...) and percent-encoding exactly.

Do not normalize drive letters, slashes, or case.

Identifiers

umid_chain is ordered nearest → furthest; values are string forms.

Nullability rules

Use null when a field is unknown/unavailable (e.g., missing DiskLabel).

Always include keys; never omit required keys.

Parameter & keyframe capture

All OperationGroup parameters must be captured:

Static values via Value.

Animated via PointList → ControlPoint (Time/Value).

Convert rationals to floats where possible. If not possible, keep textual form in parameters or keyframes[*].v.

Minimal valid example
{
  "project": { "name": "MyTimeline", "edit_rate_fps": 25.0, "tc_format": "NDF" },
  "timeline": {
    "name": "MyTimeline.Exported.01",
    "start_tc_frames": 3600,
    "events": [
      {
        "id": "ev_0001",
        "timeline_start_frames": 0,
        "length_frames": 100,
        "source": {
          "path": "file:///Volumes/Media/clip01.mov",
          "umid_chain": ["{UMID-A}", "{UMID-B}"],
          "tape_id": null,
          "disk_label": "DISK01",
          "src_tc_start_frames": 90000,
          "src_rate_fps": 25.0,
          "src_drop": false
        },
        "effect": {
          "name": "(none)",
          "on_filler": false,
          "parameters": {},
          "keyframes": {},
          "external_refs": []
        }
      }
    ]
  }
}

Rich example (clip + effect on filler)
{
  "project": { "name": "DocSeries_EP1", "edit_rate_fps": 25.0, "tc_format": "NDF" },
  "timeline": {
    "name": "DocSeries_EP1.Exported.01",
    "start_tc_frames": 3600,
    "events": [
      {
        "id": "ev_0001",
        "timeline_start_frames": 0,
        "length_frames": 250,
        "source": {
          "path": "//RadiantNexis00/Share/Media/CamA/shot_001.mov",
          "umid_chain": ["{UMID-Master}", "{UMID-Source}"],
          "tape_id": "A001R1AB",
          "disk_label": "RADIANT01",
          "src_tc_start_frames": 86400,
          "src_rate_fps": 25.0,
          "src_drop": false
        },
        "effect": {
          "name": "(none)",
          "on_filler": false,
          "parameters": {},
          "keyframes": {},
          "external_refs": []
        }
      },
      {
        "id": "ev_0002",
        "timeline_start_frames": 250,
        "length_frames": 125,
        "source": null,
        "effect": {
          "name": "AVX:SomeVendor:PanZoomLike",
          "on_filler": true,
          "parameters": {
            "Scale": 1.05,
            "Path": "file:///Users/artist/Stills/still_001.tif"
          },
          "keyframes": {
            "Scale": [
              { "t": 0.0, "v": 1.0 },
              { "t": 3.0, "v": 1.05 }
            ]
          },
          "external_refs": [
            { "kind": "image", "path": "file:///Users/artist/Stills/still_001.tif" }
          ]
        }
      }
    ]
  }
}

NDJSON option (streaming)

Instead of one large JSON, you may stream one event per line (plus a header record). Example:

{"project":{"name":"DocSeries_EP1","edit_rate_fps":25.0,"tc_format":"NDF"},"timeline":{"name":"DocSeries_EP1.Exported.01","start_tc_frames":3600}}
{"event":{"id":"ev_0001","...":"..."}}
{"event":{"id":"ev_0002","...":"..."}}


When using NDJSON, ensure consumers reconstruct the header before reading events.

Validation checklist

 project.edit_rate_fps is a float; NTSC rates use 23.976/29.97/59.94.

 project.tc_format is "DF" or "NDF".

 timeline.start_tc_frames is an int (frames).

 Every event has id, timeline_start_frames, length_frames.

 source present (object) for clips; null for pure effects.

 effect present for every event; "(none)" for plain clips.

 Keyframes use seconds ("t": float) and numeric or string values.

 Paths keep original encoding and UNC formatting.

 All required keys exist even if their values are null.

Versioning & breaking changes

This schema is canonical.

Changes must be additive (new optional fields).

Do not rename or remove existing keys.

If a major change is unavoidable, bump a top-level "schema_version" (not required today).

Potential future optional fields (additive only):

timeline.note (string)

event.role (string; e.g., “V1”, “SFX”)

effect.metadata (object; vendor-specific extractions)

source.hash (string; file integrity)

End of spec.
