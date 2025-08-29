# Collaboration Protocol: Multi-AI Coding & Execution Workflow

This protocol defines how Claude (CL), ChatGPT (GPT), and GitHub Copilot (CO) collaborate on **aaf2resolve-spec** with high uptime, deterministic handoffs, and auditability.

## Core principles
- **/docs are gospel.** Code must implement the specs; specs don’t adapt to code.
- **Canonical JSON is the only contract** between parsing and writing.
- **Baton-pass continuity**: CL → GPT → CO, with automatic fallbacks and explicit handoff notes.
- **Everything traceable**: file headers, handoff YAML, and PR descriptions reference spec sections.

---

## Roles

### Claude (CL) — Spec Guardian + Coder
- Confirms rules from `/docs` before writing code.
- Produces **verbose, end-to-end drafts** with logging and intermediate state dumps.
- Includes **handoff notes** and **resume markers** in drafts.
- Treats correctness and traceability as the quality bar.

### ChatGPT (GPT) — Executor + Verifier + Patcher
- Runs Python (incl. `aaf2`/`pyaaf2`) in sandbox or on the user’s PC when asked.
- Executes CL/CO outputs, validates against schema, and compares to Golden JSONs.
- Produces **reports, diffs, and targeted patches**.
- Continues CL’s work when sessions expire.

### GitHub Copilot (CO) — Architect & Refiner
- Converts drafts into **modular, maintainable components**.
- Implements **plugin/rule-pack architecture** post-MVP.
- Submits **PRs with atomic diffs**, spec references, and rationales.
- Keeps interfaces clean and future-proof.

### User — Integrator & Spec Guardian
- Opens issues with acceptance criteria referencing `/docs`.
- Chooses which agent to start with, approves merges.
- Ensures spec ambiguities found by code are resolved in `/docs`.

---

## Baton-Pass & Fallback Rules

**Default order:** **CL → GPT → CO**

**Auto-pass triggers**
- **CL session timeout / token limit** → **GPT continues** from last resume marker.
- **CL unavailable > 5 hours** → **GPT continues**, mark handoff “CL-unavailable fallback”.
- **GPT blocked by tool limits or needs refactor** → **CO** refactors or modularizes; hands back to GPT for execution.
- **CO waiting on draft** → **CL** produces draft; if CL unavailable, **GPT** provides minimal draft and flags “CO-first refactor”.

**Continuity guarantees**
- Every artifact has a header block (see below) and an entry in `/handoff/handoff.yml`.
- Each draft includes **“GPT Resume Here”** comments at safe breakpoints.
- Each baton pass updates `handoff.yml` with `owner`, `status`, `next_action`, and `artifacts`.

---

## Handoff YAML (store at `/handoff/handoff.yml`)

```yaml
owner: "CL"                  # CL | GPT | CO
status: "in_progress"        # in_progress | needs_review | blocked | completed
artifacts:
  - path: "src/validate_canonical.py"
    revision: "1.001"
    last_editor: "CL"
    handoff_notes: "Complete through reason code mapping. GPT should implement additional validations starting line 180."
outputs_expected:
  - "reports/validation/minimal_example.json"
  - "reports/validation/failing_examples.json"
acceptance_criteria:
  - "Schema validates minimal example"
  - "40+ reason codes implemented"
next_action: "GPT: Execute validator on test cases, generate reports"
budget:
  token_daily_max: 100000
  calls_daily_max: 1000
  if_exceeded: "Gracefully halt, update handoff.yml, pass baton to next agent"
Keep historical snapshots in /handoff/archive/.

File Header Metadata (top of any generated/edited file)
text
Copy code
# @created_by: CL | GPT | CO
# @created_at: 2025-08-29T12:00:00Z
# @revision: 1.001
# @last_editor: CL | GPT | CO
# @draft_kind: first_draft | edit | refactor | patch
# @spec_compliance: ["inspector_rule_pack.md §1.1", "data_model_json.md §Event"]
# @handoff_ready: true
# @integration_points: ["validate_canonical_json()", "write_fcpxml()"]
# @inputs: ["tests/samples/minimal_valid.json"]
# @outputs: ["reports/validation/minimal_example.json"]
# @ci_run: "<GITHUB_RUN_ID or SHA>"
# @dependencies: ["jsonschema>=4.0"]
# @reviewed_by: "owen"
# @notes: "Resume at 'GPT Resume Here' marker if CL unavailable."
CI “Must Pass” Gates
Block merges if any fail:

Canonical JSON schema validation (all samples).

Golden tests (generated vs expected canonical JSON).

Spec lint: files quote exact spec sections used (simple text check).

Path fidelity tests: no normalization of UNC/percent-encoding/drive letters.

Required keys present; unknowns = null (never omit required keys).

Python lint/format: Black, Ruff.

No writer reading AAF/DB directly (import safety).

(Post-MVP) Plugin loading/integrity tests.

Orchestration & Storage
Start with GitHub Actions (no extra hosting cost).

Use GitHub Secrets for API keys (rotate quarterly; least privilege).

Put logs & outputs in:

/logs/ for traversal/debug logs

/reports/ for validator & diff reports

/handoff/ for baton state

Large AAF inputs live outside the repo; keep tiny goldens or pointers only.

Repo Structure Additions
bash
Copy code
/handoff/
  handoff.yml
  templates/
  archive/
/logs/
/reports/
/docs/design_notes/
VS Code & Local Automation
VS Code recommended for local dev.

CL/GPT/CO will reference commands and paths that work in a VS Code terminal.

If a PR needs local generation (e.g., pyaaf2 over a test AAF), GPT will provide a ready-to-run command block and expected outputs under /reports/.

Incident & Budget Handling
If any agent exceeds daily token/call budgets, they must:

update /handoff/handoff.yml with status: blocked, reason, and consumption,

set next_action to pass baton,

stop gracefully without partial commits.

End of protocol.
