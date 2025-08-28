Contributing to aaf2resolve-spec

Thanks for helping improve this spec-first, JSON-first knowledge base and scaffolding for converting Avid AAF → FCPXML 1.13 (Resolve).

This repository is primarily documentation and contracts. Code in /src must follow the docs in /docs — never the other way around.

🧭 Contribution Philosophy

Docs are authoritative.

Canonical JSON schema lives in docs/data_model_json.md
.

Traversal, UMID resolution, and effects rules live in docs/inspector_rule_pack.md
.

Legacy behavior and rationale live in docs/legacy_compressed_json_rules.md
.

Resolve writer rules are in docs/fcpxml_rules.md
.

Spec changes precede code.
If behavior needs to change, update docs first, then implement.

Authoritative-first source resolution.
Resolve source metadata at the end of the UMID chain:
SourceClip → MasterMob → SourceMob → ImportDescriptor → Locator(URLString)
Comp-level mirrors are fallback only when the chain is broken.

Path fidelity.
Preserve UNC, percent-encoding, drive letters exactly. No normalization.

No filtering.
Capture all OperationGroups (AVX/AFX/DVE), including effects on filler.

Nullability & shape.
Required keys are always present. Unknown values = null.
Emitted/consumed structure must match data_model_json.md exactly.

🧩 Where Things Live

/docs — THE BRAIN (specs/rules/contracts)

/src — THE HANDS (scaffolds only; docstrings, TODOs, CLIs)

/tests — golden JSON/FCPXML samples (optional; recommended)

🤖 Using Claude / Copilot (Very Important)

Before any code, assistants must:

Confirm understanding of the repo’s purpose and rules.

Summarize how they will traverse the CompositionMob, resolve UMIDs, capture effects, and map to canonical JSON.

Stay out of code until explicitly told to implement.

When allowed to implement, assistants must:

Adhere strictly to /docs (quote sections when making decisions).

Never normalize paths.

Never drop OperationGroups.

Keep required keys and null semantics.

Keep writers as pure JSON→XML transforms (no AAF/DB access in writer).

✅ Contributor Checklist (before a PR)

If you change behavior:

 Update relevant docs in /docs (and link the diff in your PR).

 If needed, add/adjust golden samples in /tests/expected_outputs/.

If you write code:

 Ensure code matches the docs exactly; no ad-hoc logic.

 Do not read AAF/DB from the writer; it must only read canonical JSON.

 Preserve all path strings byte-for-byte.

 Include minimal unit/contract tests or a tests/run_golden_tests.py update.

 Add/keep docstrings pointing to the exact /docs sections used.

If you add files/structure:

 Update README.md and/or docs/in_memory_pipeline.md if layout changes.

🧪 Tests (recommended)

Create (or update):

tests/expected_outputs/canonical_min.json — a tiny valid canonical JSON.

tests/expected_outputs/min.fcpxml — the corresponding minimal FCPXML 1.13.

tests/run_golden_tests.py — asserts required keys, shapes, and simple invariants.

Golden tests help ensure code changes don’t drift from the spec.

📝 Commit Messages

Use clear, conventional messages:

docs: clarify authoritative-first UMID rule

spec: add keyframe value typing note

scaffold: add TODOs in build_canonical

writer: honor 1001/24000s frameDuration at 23.976

tests: add canonical_min.json and min.fcpxml

If a commit changes behavior, reference the doc section that justifies it.

🔒 Boundaries & Don’ts

Don’t normalize or “fix” paths.

Don’t filter out effects.

Don’t emit shapes that deviate from data_model_json.md.

Don’t read from AAF/DB in the writer—writer is JSON→XML only.

Don’t bypass /docs; propose spec changes first.

📖 Prerequisites & References

AAF SDK / pyaaf2 (Python aaf2): https://pyaaf.readthedocs.io/en/latest/index.html

AAF Inspector (lawson-tanner): https://github.com/lawson-tanner/AAFInspector/tree/main

FCPXML: https://fcp.cafe/developers/fcpxml/

Contributors are expected to be fluent with these materials.

🛠️ Development Flow

Open an issue describing change (bug/spec/feature).

Discuss proposed spec updates; agree on doc edits.

Update /docs first; push a doc-only PR if substantial.

Implement in /src per docs; add/adjust tests.

Open PR referencing issues and relevant doc sections.

Review focuses on doc alignment, fidelity, and invariants.

📜 License

MIT — see LICENSE.
