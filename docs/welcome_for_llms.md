⚡ “This is the spec-first, JSON-first pipeline for AAF → Resolve FCPXML. Canonical JSON is the single source of truth; /docs define the rules, /src only implements them.”

Welcome Brief for LLMs (Claude, Copilot, Gemini, ChatGPT)

⚠️ Important: This document is intended for Claude, Copilot, or any other LLM contributor.
It provides the onboarding context that must be confirmed before any code is written.
LLMs must remain in design/explanation mode until explicitly instructed to implement.

✅ Confirmed Understanding

Project Purpose
A spec-first, JSON-first pipeline converting Avid AAF sequences into FCPXML 1.13 for DaVinci Resolve import, avoiding proprietary APIs through deterministic, lossless extraction.

Canonical JSON Schema

Single source of truth defined in docs/data_model_json.md
.

Required keys are always present.

Unknown values = null.

Exact type specifications for project/timeline/events structure.

Traversal & UMID Resolution

Defined in docs/inspector_rule_pack.md
.

Authoritative-first resolution follows:
SourceClip → MasterMob → SourceMob → ImportDescriptor → Locator(URLString)

CompositionMob mirrors are fallback only when chain is broken.

Legacy compressed JSON looked comp-local because the exporter already inlined chain-end values.

Path Fidelity

Preserve UNC paths, percent-encoding, and drive letters exactly as found.

Never normalize or rewrite path strings.

Maintain byte-for-byte fidelity from AAF to FCPXML.

Effect Completeness

All OperationGroups captured (no filtering), including filler effects.

Extract all parameters, keyframes, and external references.

Decode Pan & Zoom stills from UTF-16LE blobs when present.

Repository Structure

/docs → The Brain (authoritative specifications/contracts).

/src → The Hands (scaffolding only, must follow /docs without improvisation).

🎬 Project Overview

This repository defines a spec-first, JSON-first pipeline for converting Avid AAF sequences into FCPXML 1.13 compatible with DaVinci Resolve.
It ensures lossless, deterministic conversion with full metadata and effects preservation.

🔑 Core Workflow

Parse AAF (via pyaaf2)
Traverse top-level CompositionMob, extract events, resolve authoritative source metadata via UMID chain.

Canonical JSON

Schema defined in docs/data_model_json.md
.

Single source of truth.

Optional SQLite Layer

Schema in docs/db_schema.sql
.

For analytics and validation only.

FCPXML Export

Resolve 1.13 compliant, per docs/fcpxml_rules.md
.

Writers must consume canonical JSON only.

📖 Key Principles

Authoritative-first resolution
Always resolve metadata via UMID chain; CompositionMob mirrors are fallback only.

Path fidelity
Preserve UNC/percent-encoding/drive letters byte-for-byte.

No filtering
Capture all OperationGroups (AVX/AFX/DVE), including filler effects.

Schema compliance
Required keys always present. Unknown = null. Exact types per schema.

📚 Repository Architecture

/docs — The Brain

data_model_json.md: Canonical JSON schema.

inspector_rule_pack.md: Timeline traversal, UMID resolution, effect extraction.

fcpxml_rules.md: Resolve FCPXML 1.13 quirks & compliance.

legacy_compressed_json_rules.md: Historical context & validation reference.

project_brief.md: Goals, pain points, context.

/src — The Hands

build_canonical.py: Spec-first scaffold for AAF → JSON.

parse_aaf.py: CLI wrapper calling build_canonical.

write_fcpxml.py: JSON → FCPXML writer scaffold.

load_db.py: JSON → SQLite loader (optional).

🧭 Timeline Selection & Traversal Rules

Select CompositionMob preferring .Exported.01.

Use picture track only; skip audio/data.

Walk Sequence.Components in playback order, maintaining absolute offsets.

Yield events for SourceClips and OperationGroups-on-filler.

Resolve authoritative source metadata via UMID chain.

🚫 Critical Boundaries

Writers read canonical JSON only (never AAF or DB).

Database is optional helper, not required for pipeline.

Docs drive implementation — never the reverse.

Legacy compressed JSON rules are for traceability, not prescriptive behavior.

✅ Working With This Repo

Before implementing:

Confirm understanding of project purpose and workflow.

Review relevant /docs specs.

Stay in design mode until explicitly told to code.

When implementing:

Quote spec sections when making decisions.

Follow Inspector Rule Pack traversal semantics exactly.

Preserve all paths and metadata byte-for-byte.

Capture all effects without filtering.

Maintain required keys and nulls.

Never:

Normalize or rewrite paths.

Filter out OperationGroups.

Omit required keys.

Read AAF/DB from FCPXML writer.

Invent ad-hoc logic outside of docs.

🎯 Reminder

This is a specification-driven project:

/docs define the rules and contracts.

/src implements them exactly.

Canonical JSON is the single source of truth.

The goal is deterministic, lossless conversion of AAF → Resolve FCPXML with full metadata fidelity.
