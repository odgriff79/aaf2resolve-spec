# Synthesis Pitch: ChatGPT + Claude + Copilot

This document consolidates the three credible pitches (ChatGPT, Claude, GitHub Copilot) into a unified strategy for the **aaf2resolve-spec** project.

---

## Core Idea
A spec-first, JSON-first pipeline for converting Avid AAF → Resolve FCPXML 1.13.
Implementation must be **deterministic, lossless, and traceable**.

---

## Why Hybrid?
- **ChatGPT** provides **execution discipline** via its 30/60/90 milestone roadmap.
- **Claude** enforces **quality and trust** with contract-driven validation, logging, and professional credibility.
- **GitHub Copilot** ensures **future extensibility** with a modular, rule-pack architecture inspired by OTIO.

Together, these form a progression:

1. **Get it working** (ChatGPT: structure, milestones)
2. **Get it right** (Claude: validation, fidelity, editor trust)
3. **Get it sustainable** (Copilot: modular plugin/rule-pack design)

---

## Roadmap

### Phase 1 (Weeks 1–4) → ChatGPT’s Day 30 Goals
- Build **Golden AAF test suite** (simple cuts, AVX filler FX, broken UMIDs, nested sequences).
- Hand-author expected canonical JSON for each test.
- Implement **schema validator** for canonical JSON (`docs/data_model_json.md`).
- Enforce spec compliance as the non-negotiable contract.

### Phase 2 (Weeks 5–8) → Claude’s Validation-First MVP
- Implement minimal parser (`build_canonical_from_aaf()`) with **maximum logging**.
- Generate extensive intermediate dumps at each traversal step.
- Add contract-driven tests:
  - UMID authoritative-first resolution
  - Byte-for-byte path preservation
  - Required key presence (null for unknowns)

### Phase 3 (Weeks 9–12) → Copilot’s Modular Refactor
- Refactor traversal + extraction into **plugin/rule-pack modules**.
- Build **Effect Parameter Explorer** and **interactive inspector** (optional).
- Begin incremental FCPXML writer following `docs/fcpxml_rules.md`.
- Support round-trip validation: AAF → JSON → FCPXML → Resolve → FCPXML → compare.

---

## Success Criteria
- ✅ 100% schema compliance for Golden AAFs.
- ✅ No path normalization; byte-for-byte fidelity preserved.
- ✅ All OperationGroups captured (no filtering).
- ✅ Round-trip tests succeed with Resolve.
- ✅ Architecture supports adding new traversal/extraction rules without rewriting core.

---

## Roles in the Hybrid
- **ChatGPT = “Get it done, on time.”**
- **Claude = “Get it right, every time.”**
- **Copilot = “Keep it future-proof and easy to change.”**

---

## Next Action
Lock this synthesis as the north star for the project.
Future pitches or contributions should be measured against this strategy:
Does it help us **get it working, get it right, or get it sustainable**?
