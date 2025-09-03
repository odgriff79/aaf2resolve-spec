# AAF Parser MAJOR SUCCESS (2025-09-03T17:20Z)
## Version: PARSER_RULES:v20250903-1720:use-mob-and-mob_id-attributes

## BREAKTHROUGH ACHIEVED:
- **71 total events** (target: ~71-72) ✅
- **35 Media+Effect, 36 FX-only** (correct distribution) ✅  
- **35/35 sources resolved** (was 0/35) ✅
- **Real clip names**: B006_C020_012989_001.new.01, A004_C020_0430NW.new.01
- **Real UMIDs**: urn:smpte:umid:060a2b34.01010105.01010f10.13000000...
- **Parameters working**: 71 clips with varying param counts (4, 58, 9)
- **Real effect names**: AVX2 Effect : EFF2_BLEND_RESIZE, Image : EFF_SUBMASTER

## Key Technical Fixes:
1. **Deep traversal**: Use OperationGroup.segments (not input_segments)  
2. **Source resolution**: Use SourceClip.mob and SourceClip.mob_id attributes
3. **Parameter extraction**: OperationGroup params properly attached to events

## Architecture: AAF → pyaaf2 → deep traversal → source resolution → canonical JSON
## Status: Core parser functionality COMPLETE

