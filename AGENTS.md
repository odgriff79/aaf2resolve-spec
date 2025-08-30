# AGENTS.md
## Mission
This repo uses multiple AI agents (Copilot coding agent, Claude Code, Gemini CLI) to propose PRs that pass CI and match our style.

## Ground Rules
- Lint: `ruff check .` (no warnings)
- Typecheck: `mypy --strict src/`
- Tests: `pytest -q`
- Commits: Conventional Commits (feat:, fix:, chore:)
- PRs: include a short “why” section and a checklist of passing CI jobs.

## Task Routing
- **Claude**: refactors, multi-file changes, RFC PRs.
- **Gemini**: test generation, docstrings, issue triage.
- **Copilot coding agent**: small fixes, integrating feedback comments.
