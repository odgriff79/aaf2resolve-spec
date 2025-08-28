# Backlog (MVP → Beta)

## MVP
- [ ] Parser (in-memory): `src/build_canonical.py` per `inspector_rule_pack.md`
- [ ] Inspector hooks: right-click probes + “Build Canonical Timeline”
- [ ] Writer: `src/write_fcpxml.py` (accept in-memory dict; CLI shim can read JSON)
- [ ] Two golden AAFs → JSON in `tests/expected_outputs/`

## Beta
- [ ] UTF-16LE path decode robustness tests (Pan&Zoom stills)
- [ ] More AVX param types (enums, booleans, matrices)
- [ ] Deeper metadata crawl (UserComments vs MobAttributeList diffs)
- [ ] DF/NDF edge cases at non-integer rates (23.976/29.97/59.94)
- [ ] Asset de-duplication by path (writer)

## Nice-to-have
- [ ] Export Canonical JSON / Export Compressed JSON (diagnostics)
- [ ] CI: validate JSON against schema; FCPXML sanity checks
- [ ] NDJSON export mode (streaming events)
