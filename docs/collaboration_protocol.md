# Collaboration Protocol: Multi-AI Coding & Execution Workflow

This document defines how multiple AI systems (Claude, GitHub Copilot, ChatGPT) will collaborate on the **aaf2resolve-spec** project.  
The intent is to maximize quality, redundancy, and validation by combining their different strengths.

---

## 🎭 Roles

### Claude (Spec Guardian + Coder)
- Confirms exact rules from `/docs` before implementation.  
- Produces **end-to-end code drafts** that are clear, verbose, and aligned to the spec.  
- Always includes **logging, intermediate state dumps, and validation hooks**.  
- Acts as the **quality bar setter**: correctness and traceability first.

### GitHub Copilot (Architect & Refiner)
- Produces **diff-style patches** for integration into `/src`.  
- Focuses on **modularity, plugin/rule-pack architecture, and long-term maintainability**.  
- Refactors Claude’s verbose drafts into sustainable, reusable components.  
- Ensures interfaces remain clean and aligned with the spec.

### ChatGPT (Executor + Patcher)
- Runs **pyaaf2** and Python code in sandbox or on the user’s PC.  
- Executes both Claude and Copilot’s implementations, comparing outputs.  
- Validates canonical JSON against `/docs/data_model_json.md`.  
- Provides **logs, diffs vs Golden JSONs, and validation reports**.  
- Suggests **patches or simplifications** when code fails tests.

### User (Integrator)
- Opens GitHub issues describing tasks, with acceptance criteria referencing `/docs`.  
- Decides when to request input from one or more AIs.  
- Curates outputs, selects the best combination, and commits validated changes.  
- Guards the rule: **“/docs are gospel; code must follow docs, never redefine them.”**

---

## 🔄 Workflow

### 1. Spec/Issue Creation (User)
- Open a GitHub issue with clear acceptance criteria.
- Example: *“Implement authoritative UMID chain traversal for SourceClips per inspector_rule_pack.md §3.1–3.5.”*

### 2. Spec/QA Pass (Claude)
- Reviews relevant `/docs`.  
- Restates the rules in plain language for traceability.  
- Produces an **initial full implementation draft**, prioritizing clarity and logging.

### 3. Architectural Pass (Copilot)
- Refactors or rewrites Claude’s draft into **modular components**.  
- Provides diff-style patches scoped to `/src`.  
- Ensures future extensibility via **rule-pack/plugin architecture**.

### 4. Execution & Debugging (ChatGPT)
- Runs both implementations against test AAFs.  
- Validates output JSON against the canonical schema.  
- Diffs against **Golden JSONs** when available.  
- Reports errors, logs, and proposes targeted patches.

### 5. Integration (User)
- Reviews outputs from Claude, Copilot, and ChatGPT.  
- Selects the best blend (e.g., Claude’s logging + Copilot’s modularity + ChatGPT’s patch).  
- Commits only **validated and schema-compliant** code.  
- Updates `/docs` if ambiguities or gaps are revealed.

---

## ⚖️ Why This Works

- **Claude** = Quality and Spec Fidelity (get it *right*).  
- **Copilot** = Modularity and Extensibility (keep it *maintainable*).  
- **ChatGPT** = Execution and Verification (prove it *works*).  
- **User** = Integrator and Spec Guardian (keep it *on-track*).

This redundancy ensures:
- At least **two independent code proposals** per issue.  
- Automated execution and schema validation.  
- Incremental confidence: get it working → get it right → keep it sustainable.

---

## 📌 Key Rules
- `/docs` define truth. `/src` must follow, not improvise.  
- Writers **only consume canonical JSON** — never AAF or DB directly.  
- Path strings (UNC, percent-encoding, drive letters) must be preserved byte-for-byte.  
- All OperationGroups (effects) must be captured — **no filtering**.  
- All required JSON keys must exist — missing values = `null`, never omission.

---

End of protocol.
