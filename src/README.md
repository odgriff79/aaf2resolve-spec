/src — Implementation Scaffolding

This folder contains spec-first scaffolds for the AAF → JSON → FCPXML pipeline.
No file here contains traversal or extraction logic — only contracts, docstrings, and TODOs.

The authoritative behavior is defined in /docs, not here.

📦 Modules
build_canonical.py

Entrypoint: build_canonical_from_aaf()

Contract: Convert an AAF into the canonical JSON defined in docs/data_model_json.md
.

Must follow traversal, UMID resolution, and effect rules in docs/inspector_rule_pack.md
.

Authoritative-first: Resolve source metadata at the end of the UMID chain (Locator URL, SourceMob TC/rate/drop, TapeID, DiskLabel).

No filtering: Capture all OperationGroups, including filler effects.

parse_aaf.py

Thin CLI wrapper that calls build_canonical_from_aaf().

Writes the canonical JSON to stdout or file.

Must not add or transform fields.

write_fcpxml.py

Consumes canonical JSON only.

Outputs Resolve-compatible FCPXML 1.13 per docs/fcpxml_rules.md
.

Pure JSON → XML transform.

Writers must never query AAF or DB directly.

load_db.py

Optional: Load canonical JSON into a SQLite database per docs/db_schema.sql
.

Useful for queries, analytics, and validation.

DB is not required for the pipeline — JSON remains the single source of truth.

⚖️ Core Principles

Canonical JSON is the contract

All code here must emit or consume the structure in docs/data_model_json.md
.

Required keys always present, missing values = null.

Authoritative-first resolution

Always resolve source metadata via UMID chain:
SourceClip → MasterMob → SourceMob → ImportDescriptor → Locator(URLString)

CompositionMob mirrors are fallback only.

Path fidelity

Preserve UNC, percent-encoding, drive letters as-is.

Never normalize or rewrite paths.

No filtering

Capture all OperationGroups (AVX/AFX/DVE), including filler effects.

Spec-driven development

/docs defines the “what.”

/src implements the “how,” exactly as described.

No improvisation — all logic must trace back to a documented rule.

🚦 Development Flow

Start with docs → read /docs/data_model_json.md and /docs/inspector_rule_pack.md.

Implement scaffolds → fill in build_canonical.py, write_fcpxml.py, etc.

Test against docs → validate canonical JSON, ensure output matches schema.

Iterate → refine implementations only by updating docs first, then code.

This README ensures contributors (Claude, Copilot, or human) understand:
/src is scaffolding that must strictly follow /docs.
