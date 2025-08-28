# aaf2resolve-spec

**Spec-first, JSON-first pipeline for converting Avid AAF → Resolve FCPXML 1.13**

This repository defines a deterministic, lossless approach to timeline interchange.  
It is **not just code**, but a **knowledge base + specification** to guide robust, professional-grade implementations.

---

## 🎯 Purpose
- Convert **Avid AAF sequences** into **DaVinci Resolve FCPXML 1.13**
- Avoid proprietary APIs by using **open-source pyaaf2**
- Preserve **all metadata and effects** with authoritative fidelity

---

## 📚 Key Principles
- **Canonical JSON** (`/docs/data_model_json.md`) is the **single source of truth**
- **Authoritative-first UMID resolution**:  
  `SourceClip → MasterMob → SourceMob → ImportDescriptor → Locator(URLString)`
- **Path fidelity**: preserve UNC, percent-encoding, drive letters exactly (no normalization)
- **No filtering**: capture *all* OperationGroups, including filler effects
- **Spec-first discipline**: `/docs` defines contracts, `/src` follows them strictly

---

## 🧭 Roadmap (Hybrid Strategy)

We adopt a **synthesis of three credible pitches**:

- **ChatGPT → Execution Discipline**  
  30/60/90 milestone roadmap (Golden AAFs, schema validator, MVP parser, FCPXML writer)

- **Claude → Quality & Trust**  
  Validation-first approach, contract-driven tests, extensive logging, professional rigor

- **GitHub Copilot → Extensible Architecture**  
  Plugin/rule-pack design, effect parameter explorer, interactive inspector, long-term maintainability

**Progression:**  
1. *Get it working* (ChatGPT structure)  
2. *Get it right* (Claude validation)  
3. *Get it sustainable* (Copilot modularity)

---

## 📂 Repository Layout
- `/docs` — Specifications & rules (the “Brain”)  
- `/src` — Implementation scaffolding (the “Hands”)  
- `/tests` — Golden AAFs and validation harnesses (future)

Key docs:
- [`project_brief.md`](docs/project_brief.md) — Goals, context
- [`data_model_json.md`](docs/data_model_json.md) — Canonical JSON schema
- [`inspector_rule_pack.md`](docs/inspector_rule_pack.md) — Traversal, UMID, effect rules
- [`fcpxml_rules.md`](docs/fcpxml_rules.md) — Resolve FCPXML quirks
- [`legacy_compressed_json_rules.md`](docs/legacy_compressed_json_rules.md) — Traceability from past workflows
- [`pitches/synthesis.md`](docs/pitches/synthesis.md) — Agreed hybrid strategy

---

## ✅ Next Steps
- Create Golden AAF test suite  
- Implement schema validator & contract tests  
- Build minimal parser with max logging  
- Refactor into plugin/rule-pack architecture  
- Add FCPXML writer + round-trip validation  

---

💡 **Reminder:** This is a **spec-first project**.  
Documentation defines the rules. Implementations must follow them exactly.  
The canonical JSON is the only interface between parsing and writing.  
