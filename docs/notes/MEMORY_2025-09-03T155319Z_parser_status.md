# Memory Note – Parser Status (2025-09-03)

## Context
Working on **aaf2resolve-spec** parser in Codespaces:
- FX-on-filler AAFs (nested SourceClips under OperationGroups)
- Animated parameter extraction (`VaryingValue` + `PointList`)
- Source resolution pipeline

## Achievements
- ✅ Deep traversal confirmed (71 OperationGroups, 35 with nested SourceClips)
- ✅ 603 animated parameters found (e.g., AFX_POS_X_U, AFX_SCALE_X_U)
- ✅ Rational values (fractions) decoded correctly
- ✅ iter_parameters() helper added
- ✅ Early-return on missing source_id removed, resolver call guarded
- ✅ Commits pushed: deep traversal + keyframe detection confirmed

## Blockers
- ❌ Source resolution failing (all 36 SourceClips report "no source_id")
- ❌ Parameters not attached in JSON (0 animated params exported)
- ❌ Patch attempt missed clip dict injection in _process_source_clip

## Next Steps
- Finalize _process_source_clip:
  - Replace source_id reliance with resolver
  - Attach OG parameters (iter_parameters + extract_keyframe_timing_data)
- Re-run canonical build:
  - Expect ~72 events (≈36 clips + ≈36 effects)
  - Confirm animated params attached
- Commit + push when fixed

## Version Stamp
`PARSER_RULES:v20250903-0930:deepwalk+pointlist603+resolver-guard-noattach`
