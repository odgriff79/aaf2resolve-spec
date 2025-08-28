AAF to Resolve FCPXML Converter
🎯 Purpose

This project defines a spec-first, JSON-first pipeline for converting Avid AAF sequences into FCPXML 1.13 for DaVinci Resolve.
It avoids proprietary APIs and ensures lossless, deterministic extraction of AAF semantics, metadata, and effects.

🔑 Core Workflow

Parse AAF (via pyaaf2)

Traverse the top-level CompositionMob (picture track only).

Yield events for SourceClips and OperationGroups.

Resolve authoritative source metadata via UMID chain.

Canonical JSON Schema

All extracted data is written into the canonical JSON structure (docs/data_model_json.md).

This JSON is the single source of truth for all writers.

Optional SQLite Layer

Normalized relational schema (docs/db_schema.sql) for analysis, queries, and validation.

Export FCPXML 1.13

Writers consume the canonical JSON only.

Output follows Resolve quirks (docs/fcpxml_rules.md).

📖 Project Principles

Schema-driven: Canonical JSON defines the contract; all code must follow it.

Authoritative-first resolution:

Source path, TapeID, DiskLabel, timecode/rate/drop are always taken from the end of the UMID chain:
SourceClip → MasterMob → SourceMob → ImportDescriptor → Locator(URLString)

Comp-level mirrors are used only if the chain is broken.

Legacy compressed JSON looked self-contained because the Inspector exporter had already inlined chain-end values.

Lossless capture: All timeline semantics, AVX/AFX/DVE effects, parameters, keyframes, and external refs are preserved.

Path fidelity: UNC paths, percent-encoding, drive letters are preserved exactly. No normalization.

No filtering: All OperationGroups are captured, even filler effects.

Required fields: Always present in JSON. Missing values = null.

📚 Documentation Map

This repository is primarily a knowledge base.
All rules and semantics are in /docs. The /src code scaffolding must follow them.

Project Brief → goals, pain points, context (docs/project_brief.md)

Canonical Data Model → JSON schema (single source of truth) (docs/data_model_json.md)

Database Schema → optional relational model (docs/db_schema.sql)

FCPXML Rules → Resolve 1.13 quirks & compliance (docs/fcpxml_rules.md)

In-Memory Pipeline → architecture for direct parsing with pyaaf2 (docs/in_memory_pipeline.md)

Inspector Rule Pack → traversal, UMID resolution, effect extraction (docs/inspector_rule_pack.md)

Legacy Compressed JSON Rules → flattened export method (kept for traceability) (docs/legacy_compressed_json_rules.md)

Backlog → open features & tasks (docs/backlog.md)

💡 Key principle: Writers and downstream tools must always consume canonical JSON.
The database and legacy compressed JSON paths are optional helpers, not dependencies.

📦 Implementation Status

/docs → fully populated specifications.

/src → scaffolding for parser, writer, DB loader. Must follow docs.

Tests and examples to follow.

🔗 References & Prerequisites

AAF SDK / pyaaf2 docs → pyaaf.readthedocs.io

AAF Inspector (lawson-tanner) → github.com/lawson-tanner/AAFInspector

FCPXML specification → fcp.cafe/developers/fcpxml

✅ This README ensures any new contributor (Claude, Copilot, or human) has the full context up front, including the authoritative-first rule and why legacy JSON looked different.
