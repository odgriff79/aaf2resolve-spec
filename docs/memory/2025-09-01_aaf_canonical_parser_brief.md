# Project Brief: AAF to Canonical JSON Parser  
**Date:** 2025-09-01  
**Stage:** Memory checkpoint  

## Objective  
Build a canonical AAF → JSON → FCPXML pipeline for DaVinci Resolve that matches the behavior of a working legacy parser.  

## Current Status  
- Using `pyaaf2` to parse AAF files into expanded JSON format (per repo spec).  
- **Target:** 71 events for `candidate.aaf` test file (legacy parser’s 72nd event was an error).  
- **Current result:** 71 events — correct count but wrong distribution.  

## Key Discovery from Legacy CSV Analysis  
- Legacy parser found 71 valid events, each with **both clip and effect**.  
- Example:  
  - Event 1: `B006_C020_012989_001.mov` + AVX2 Effect: Resize  
  - Event 2: `A004_C020_0430NW_001.R3D` + Image: Stabilize  
- All 71 events follow this pattern: no standalone clips, no effect-only events.  

## Current Problem — Wrong Distribution  
- Canonical builder finds 71 events but categorizes incorrectly:  
  - **Media + Effect:** 3 events (should be 71!)  
  - **Effect only:** 68 events (should be 0!)  
  - **Missing:** 68 OperationGroups that should contain SourceClips.  

## Root Cause  
- Recursive SourceClip detection in OperationGroup inputs isn’t finding SourceClips nested deeper in the AAF structure.  
- Only 3 of 71 OperationGroups detect their SourceClip inputs properly.  

## Solution Approach  
- Fix recursive SourceClip detection: search deeper inside OperationGroup input structures.  
- Expected outcome:  
  - **71 “Media + Effect” events**  
  - **0 standalone clips**  
  - **0 effect-only events**  
- Based on legacy CSV evidence.  

## Critical Files  
- `src/build_canonical.py` → Parser needing SourceClip detection fix.  
- `tests/integration/test_compare_candidate.py` → Confirms event count match but distribution mismatch.  
- Legacy CSV confirms correct structure.  

## Next Step  
Debug why recursive SourceClip search works for only 3/71 OperationGroups instead of all 71.  

## Constraint  
Must work with expanded JSON format per repository specification.  
