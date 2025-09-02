# AAFx Brief Protocol (v0.1)

## Dictionary
MS=Milestone tag; DT=UTC ISO; VER=version or commit; E=events; M=media clips; FX=effects on filler; M+FX=media+effect events; DUPS=dup count/positions; FXN=effect naming status; SR=source resolution; KF=keyframes; CFG=parameter profile; REQ=required fields policy; ART=artifacts; TST=tests; DEC=decisions; TBC=to-be-considered; NEXT=next actions; REF=repo refs.

## Example
[AAFx v0.1]
MS=FINAL_SUCCESS_2025-09-01
DT=2025-09-01T14:32Z
VER=build_canonical.py@d563d93
E=73  M=37  FX=36
DUPS=2 @ [4372, 4441]
FXN=ok
SR=warn (some unresolved; still emitted)
KF=wip (extracting, not saved)
CFG=tiny
REQ=docs/notes/REQUIRED_FIELDS.md
ART=reports/integration/candidate_from_aaf.canonical.json
TST=compare_candidate ✅ ; fcpxml_shape ✅
DEC=keep FX names via AvidEffectID decode; defer color params
TBC=source chain to originals vs proxies; param selection tool; Resolve FCPXML exactness
NEXT=dedup @4372/4441; tighten source chain; add param inventory tool
REF=docs/milestones/AAF_Parser_FINAL_SUCCESS_BRIEF_2025-09-01.md
