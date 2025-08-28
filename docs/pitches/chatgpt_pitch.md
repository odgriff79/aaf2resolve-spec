# [Tool/Model] Pitch
Date: 2025-08-28
Source: Conversation with chatgpt

## Overview
(then paste the full pitch text exactly as written)

Request for Input (No Code Yet) I’ve prepared a full specification repository for a project called aaf2resolve-spec: 👉 https://github.com/odgriff79/aaf2resolve-spec This repo defines a spec-first, JSON-first pipeline for converting Avid AAF sequences into FCPXML 1.13 compatible with DaVinci Resolve. Key points you need to know from the repo: Canonical JSON schema in /docs/data_model_json.md is the single source of truth. Traversal, UMID resolution, and effect extraction rules are defined in /docs/inspector_rule_pack.md. Authoritative-first UMID resolution is required: SourceClip → MasterMob → SourceMob → ImportDescriptor → Locator(URLString). Path fidelity: preserve UNC, percent-encoding, and drive letters exactly (no normalization). No filtering: all OperationGroups (AVX/AFX/DVE) must be captured, including filler effects, with parameters, keyframes, and external references. Legacy compressed JSON rules are included for traceability, not as the main implementation path. Writers must only consume canonical JSON — never AAF or DB directly. /src is scaffolding only, implementation must strictly follow /docs. ⚠️ Note: The repo itself may contain errors, gaps, or incorrect assumptions. At this stage, all ideas, critiques, and observations are welcome, even if they challenge or contradict parts of the repo. What I’d like from you now: A pitch or proposal describing how you would proceed from here. Suggestions, ideas, or architectural strategies to move the project toward a working prototype. Inspirations you see from other open-source projects, industry standards, or commercial tools that might influence direction. Creative thoughts about workflow, UX, or validation/testing approaches. Absolutely no code at this stage — just reasoning, planning, and conceptual guidance. The goal is to gather diverse perspectives from different AIs, then compare their proposals before we move forward with actual implementation.
ChatGPT said:
Thought for 4 seconds

Love the brief. Here’s my proposal (no code) on how to move from “spec-first repo” → “confident working prototype,” plus ideas you can use to pressure-test the design.

Pitch: From Spec → Prototype with Confidence
North Star

A deterministic, auditable pipeline: AAF → Canonical JSON → (optional DB) → FCPXML 1.13, with authoritative-first UMID resolution, path fidelity, and no effect filtering. Writers consume JSON only.

30/60/90 Roadmap (outcomes, not outputs)
Day 30 — Prove the contract

Golden Set v1
3–5 “teaching” AAFs covering: plain cuts; OperationGroups on filler; a Pan&Zoom still with UTF-16LE path; one broken UMID chain; one mixed-rate case.

Schema-as-law
Convert docs/data_model_json.md into a machine JSON Schema; add a tiny “canon validate” CLI (JSON-in → pass/fail + rich errors).

Spec Compliance Kit
A markdown matrix mapping each rule in inspector_rule_pack.md → a specific AAF in the golden set and → an expected JSON field. (Green = covered, Grey = TBD.)

Inspector Playbook
Document how to use your Enhanced AAF Inspector to manually derive the expected canonical JSON for each golden file (ensures humans and tools agree).

Day 60 — Walking prototype, tight feedback

MVP Parser (guard-railed)
Implements traversal + UMID resolution per docs. Emits explain logs: for every event/field, say which rule produced it and which AAF node it came from.

Round-trip Testing
Golden AAF → Canonical JSON → FCPXML → Resolve import smoke test (manual for now). Start a known-quirks appendix in fcpxml_rules.md.

Fail-open Strategy
Broken chains don’t halt: fields become null, and an advisory block is appended to a validation report (never guess, never normalize).

Effect Coverage Snapshot
A small report summarizing what kinds of OperationGroups were observed, % with parameters, % with keyframes, % with external refs found.

Day 90 — Editorially trustworthy

FCPXML writer v1
Clips + timing correct; assets deduped; tcStart and frameDuration use proper fractional notation; effect parameters included only when safely mappable.

Reliability Dash
For each golden: schema pass, effect capture count, path fidelity binary check, tc math deltas (frames), Resolve import status.

Pitch Archive & Policy
Store AI pitches and decisions; add a Spec Change Protocol (PR template: “doc diff first, then code”).

Architecture & Governance (how we keep it clean)

Immutable Dataflow
Canonical JSON is read-only after creation. Any downstream transforms are pure functions with input→output diffs logged.

Feature Flags, not forks
Example: --strict (fail on any schema deviation) vs --editorial (allow null fallbacks, still log). The JSON shape never changes.

SemVer for the Schema
Add optional schema_version in canonical JSON. “Additive only” by default. Breaking changes require an RFC + migration notes.

Traceability Tags
Every event JSON carries a stable id and provenance crumbs (mob ids/UMIDs). FCPXML items include comments/attrs that reference the source event id (for human diffing).

Validation & Testing (make falsification easy)

JSON Schema + “Reason codes”
Each schema rule carries a code (e.g., CANON-REQ-05). Validation output lists failing codes so issues are googleable across tickets.

Path Fidelity Audit
Byte-for-byte comparison hash for each source.path seen; a report lists any non-identical string handling from ingest to writer (should be zero).

Timeline Math Checker
A tiny library that, given fps + DF/NDF + frame counts, computes expected tcStart and durations and asserts against emitted values.

Golden JSONs
Hand-curated canonical JSONs per golden AAF; CI diffs actual vs expected. Any change is either a regression or a spec change (docs first).

Inspector & UX (win hearts, not just tests)

Right-click → “Preview Canonical Fragment”
Shows the exact JSON snippet that would be emitted + the rule IDs used to produce each field.

UMID Graph View
Visualize chain traversal with “nearest wins” highlighting; annotate where TapeID/DiskLabel and Locator(URLString) were found.

Effect Explorer
Table of all OperationGroups with columns: on_filler, parameter count, keyframe count, external_refs discovered, suspected P&Z stills.

Diff Viewer
Side-by-side canonical JSON (expected vs actual), with rule IDs on hover to understand why differences exist.

Inspirations to borrow (no reinvention)

OpenTimelineIO — adapter model + rich test corpus, but keep your own canonical shape (don’t adopt their schema wholesale).

FFmpeg — “probe first” mindset, verbose explain logs, separation of demux vs filter vs mux (map to parse vs extract vs write).

IMF/AS-11 — industry-grade provenance and “authoritative source” principles mirror your UMID chain stance.

Commercial conform tools — they prioritize trust: predictable gaps, clear warnings, and zero mystery transforms.

Risk Register (and how we mitigate)

pyaaf2 variability / SDK drift → thin abstraction in one module; contract tests against mock objects.

Effect parameter sprawl → rule: include any parsable, common parameters; if mapping to FCPXML is ambiguous, represent minimally (no guessing).

Spec drift → “Docs first” PR rule + schema versioning + RFCs for breaking changes.

Performance → treat as non-goal until Day 60; then profile hotspots (mob map, deep traversal).

Success Metrics (measurable, not vibes)

100% schema compliance on goldens (CI).

Zero path mutations (fidelity audit).

100% OperationGroup capture on goldens.

Correct tcStart/frameDuration for NTSC/DF cases.

Resolve import passes for writer v1 goldens.

Editor feedback: “trusted conform” on a real documentary or series episode.

Where to start this week

Finalize Golden Set v1 and hand-author Golden JSON with the Inspector.

Generate JSON Schema from data_model_json.md and wire up a canon validate CLI.

Add Spec Compliance Matrix doc mapping each rule → a golden case.

Decide flags for strict vs editorial mode (behavioral, not structural).

If parts of the repo prove wrong, great — the process above is designed to surface and correct them with minimal churn: update docs → update golden JSONs → update code. That keeps everything spec-true, auditable, and easy to trust.
