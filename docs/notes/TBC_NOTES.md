# TBC Notes (append-only)

- Validate random events in canonical JSON vs legacy CSV
- Ensure source chain resolves to original camera files (not proxies)
- Selective parameter extraction (tiny/default/expanded profiles)
- Keep option to include FrameFlex data later (not now)
- Add test AA Fs + matching legacy CSVs
- Prep FCPXML generation parity with Resolve; supply legacy generator + valid Resolve exports
- Legacy FCPXML generator has OOB keyframes — track fix
- Improve “new Claude chat” bootstrap via repo briefs (avoid long intros)
- Strict versioning + date stamps in code comments for continuity
- Consider web app to compress long chats into short briefs
- Agents via ADK to write/update notes automatically
- Preference: terminal-paste commands to reduce manual steps
- Keep last-chat “golden takeaways” without blowing context tokens
- Don’t over-share archives to avoid token burn; lean on repo refs
- Track “what worked where” (commit+file anchors in notes)
- Expand tests to additional fixtures
- Parameter inventory/values/compare tools for data-driven selection
- Create REQUIRED_FIELDS.md for current minimal capture; keep editable

## 2025-09-01 Additions
- Consider compact “AAFx Brief Protocol” for compressed milestone sharing with Claude.
- Decide if repo should hold brief protocol spec vs just keep in TBC notes (may be over-effort).
- Idea: small dictionary (MS, DT, VER, E, FX, SR, etc.) to keep briefs concise.
- Debate: better to maintain long-form briefs only in milestones, skip compressed form.
- Potential alternative: use Claude/Gemini to generate short briefs from long messages.
- Key requirement: avoid manual retyping of long intros for every new chat.
- Reminder: include essential source clip metadata always; don’t let it be skipped.
- Maintain option to expand effect/clip data later (FrameFlex, color, etc.) without bloating JSON now.
- Create REQUIRED_FIELDS.md to track which fields are currently required; keep editable/expandable.
