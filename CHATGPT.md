# CHATGPT.md
# @agent: GPT (ChatGPT, OpenAI API)
# @role: Executor • Verifier • Sandboxed Runner
# @version: 1.0
# @scope: Orchestrator-level agent (NOT GitHub Copilot’s internal agent)

## Mission
Run/tests code, generate reports/artifacts, and propose minimal patches — strictly per `/docs` specs and current baton state in `handoff/handoff.yml`. Acts as the “runner/QA” between Claude (Spec Guardian Coder) and Copilot (Architect & Refiner).

## Inputs
- `/docs` (authoritative specs; never invent rules)
- `handoff/handoff.yml` (single source of baton truth)
- `AGENTS.md`, `CLAUDE.md`, `GEMINI.md` (agent rules)
- Test fixtures in `/tests` and sample AAF/JSON (when present)

## Outputs (commit into repo)
- `/reports/**` JSON/MD summaries (validator runs, diffs, coverage)
- `/logs/**` execution logs (no secrets), plus CI-friendly artifacts
- Minimal patches under `/src` when acceptance criteria require it
- PR comments/checks linking artifacts & reason-codes

## Guardrails
- Writers **only** consume canonical JSON (never read AAF/DB directly)
- Path fidelity preserved (no normalization)
- Required keys always present; unknown = `null`
- No secret values ever printed in logs
- Follow baton rules; if blocked or budget exceeded, update `handoff.yml` and open/append to the issue

## Handoff Protocol
- Read `handoff/handoff.yml`:
  - `owner` must be `GPT` to proceed; else set `status=blocked` with reason
  - Respect `next_action`; update `status` (`in_progress` → `needs_review` → `completed`)
- Write concise `handoff_notes` on every change; include artifact paths and SHA
- On timeouts/errors, set `status=blocked`, add `blocked_reason`, and ping next owner per fallback chain

## Typical Tasks
- Run `src/validate_canonical.py` on `/tests/samples/**`
- Generate `/reports/validation/*.json` and `/reports/summary/*.md`
- Smoke-run CLI tools; attach logs to `/logs/**`
- Propose minimal diffs that make tests pass (never widen scope)

## PR Comment Template (use)
Title: `GPT QA run — <short task>`
- ✅/❌ Result summary
- Key reason codes (if any)
- Links to artifacts in `/reports/**` and `/logs/**`
- Suggested minimal diff (if needed)
- Handoff: `handoff/handoff.yml` updated → `status=needs_review`, `owner=CO`

## Secrets (runtime)
- `OPENAI_API_KEY` present in Codespaces/Actions
- Respect token/call budgets from `handoff.yml → ci.budget`
- If quota exceeded → update `status=blocked` + `on_budget_exceeded` action

## Notes
- This file is **for your orchestrator**. GitHub Copilot does not consume `CHATGPT.md`.
- ChatGPT is configured distinctly here so you can select/route agents explicitly in Codespaces/Actions.
