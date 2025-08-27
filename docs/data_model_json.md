# Canonical JSON Data Model

This schema represents the canonical interchange format for AAF → FCPXML conversion. All tools operate on or emit this format.

## Schema (Draft)

```json
{
  "project": {
    "name": "Project Name",
    "rate": {"numerator": 24, "denominator": 1},
    "timelines": [
      {
        "name": "Timeline 1",
        "timecodeStart": 0,
        "events": [
          {
            "id": "ev1",
            "type": "SourceClip",
            "start": 0,
            "duration": 100,
            "track": 1,
            "source": "src1",
            "effects": []
          },
          {
            "id": "ev2",
            "type": "OperationGroup",
            "start": 100,
            "duration": 50,
            "track": 1,
            "source": "src2",
            "operation": "Dissolve",
            "effects": [
              {
                "id": "fx1",
                "type": "Dissolve",
                "params": [{"name": "duration", "value": 50}]
              }
            ]
          }
        ]
      }
    ],
    "sources": [
      {
        "id": "src1",
        "name": "V1_Clip.mov",
        "path": "/media/V1_Clip.mov",
        "rate": {"numerator": 24, "denominator": 1}
      },
      {
        "id": "src2",
        "name": "V2_Clip.mov",
        "path": "/media/V2_Clip.mov",
        "rate": {"numerator": 24, "denominator": 1}
      }
    ]
  }
}
```

## Field Notes

- **project.rate**: (rational) Edit rate for the project and default timelines.
- **timelines[].timecodeStart**: Timeline start timecode (integer, in project rate units).
- **events[].type**: `"SourceClip"` for basic clips, `"OperationGroup"` for e.g. effects/transitions.
- **events[].source**: Ref to a source object by `id`.
- **effects[]**: Optional, nested under events (for transitions, color corrects, etc).
- **sources[]**: All referenced media, with full path and rate.

### Example: SourceClip Event

```json
{
  "id": "ev1",
  "type": "SourceClip",
  "start": 0,
  "duration": 100,
  "track": 1,
  "source": "src1",
  "effects": []
}
```

### Example: OperationGroup Event

```json
{
  "id": "ev2",
  "type": "OperationGroup",
  "start": 100,
  "duration": 50,
  "track": 1,
  "source": "src2",
  "operation": "Dissolve",
  "effects": [
    {
      "id": "fx1",
      "type": "Dissolve",
      "params": [{"name": "duration", "value": 50}]
    }
  ]
}
```