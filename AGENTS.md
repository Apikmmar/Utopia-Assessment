# Workspace instructions

## Response style

Use the local [Caveman skill](.skills/caveman/SKILL.md) for chat responses in this project. Read it before first use. Keep technical details accurate and explanations clear. Follow higher-priority instructions when they conflict with the skill.

The user can disable this style by saying "normal mode" or "stop caveman", and enable it again with "caveman mode" or `/caveman`. An explicit request for more detail takes precedence over brevity. Keep persisted code, comments, and documentation in normal prose.

## Engineering skills

Read the relevant local skill before planning, implementing, refactoring, or reviewing application code:

- [Frontend](.skills/frontend/SKILL.md): application interfaces, components, styling, client state, accessibility, and frontend performance.
- [Backend](.skills/backend/SKILL.md): services, business rules, persistence, storage, authorization, and external integrations.
- [Testing](.skills/testing/SKILL.md): test planning, behavior and regression coverage, integration and end-to-end checks, and failure diagnosis. Apply it when a change needs tests or verification, alongside the relevant implementation skill.
- For changes spanning both layers, read both skills and keep their contracts aligned.

These skills apply automatically to relevant project work through these instructions. They are stored locally rather than registered in the global skill directory.

The skills are reusable across products and technology stacks. Apply relevant guidance to the current task; derive product requirements, platform choices, and business rules from that task and its applicable documentation, not from the skills.

## Review agents

For a requested specialist review, delegate to the relevant role:

- [Security reviewer](.reviewers/security-reviewer.toml): trust boundaries, access control, secret exposure, and exploitable behavior.
- [Performance and scalability reviewer](.reviewers/performance-reviewer.toml): latency, throughput, resource use, concurrency, and capacity limits.
- [Code quality reviewer](.reviewers/code-quality-reviewer.toml): correctness, maintainability, DRY, SOLID, SRP, module boundaries, and meaningful test gaps.

These are reusable role definitions in the documented custom-agent TOML format. They are not registered for native discovery in `.codex/agents/`. To use them here, read the selected file and pass its `developer_instructions` to the delegated agent together with the concrete task. Keep model settings inherited unless the user requests an override.

- Include the review scope, changed files or comparison base where available, acceptance criteria, and relevant constraints. If version control is unavailable, identify the specific files or behavior to review.
- Have each reviewer read the [shared review protocol](.reviewers/review-protocol.md) and applicable skills. Use only the relevant roles; do not spawn reviewers for every routine change.
- Reviewers report findings and leave implementation to the primary agent. Review-only instructions do not create a separate filesystem sandbox; session permissions still apply.
- Keep independent reviews separate until completion. The primary agent verifies and deduplicates findings, resolves disagreements using evidence, and owns any fixes and follow-up checks.
- Do not add an architecture reviewer until the user requests it.

## Shared engineering standards

- Read the current requirements, applicable project documentation, and relevant existing code before changing architecture. Preserve agreed choices; distinguish proposed choices from final decisions.
- Build cohesive feature modules with explicit interfaces and one-way dependencies. Keep business rules out of rendering, HTTP handlers, and infrastructure adapters.
- Apply SRP by separating responsibilities that change for different reasons. Apply DRY to repeated knowledge and business rules; extract shared code when the shared behavior is understood, rather than merging superficially similar code.
- Apply SOLID where it improves changeability: use composition and focused contracts, preserve substitutability, and inject infrastructure dependencies at meaningful boundaries. Do not require classes, interfaces, factories, or repositories for every function.
- Prefer a modular monolith and the smallest design that meets the requirement. Add distributed services, queues, caches, or abstraction layers when a concrete need justifies their operational cost.
- Make speed, security, and scalability reviewable through relevant measurements, enforced boundaries, bounded workloads, and tests. Do not claim these properties from folder structure or framework choice alone.
- Use clear names, explicit types at boundaries, centralized configuration, maintained dependencies, and the existing formatter, linter, and lockfile conventions. Never commit secrets.
- Test important behavior and failure paths at the appropriate layer. Run relevant existing checks, update setup or contract documentation when behavior changes, and report remaining limitations honestly.
- Keep refactoring scoped to the requested change. Document material tradeoffs and assumptions, and avoid speculative features or unrelated infrastructure changes.

## Caveman skill

- Name: `caveman`
- Location: `.skills/caveman/SKILL.md`
- Source: https://github.com/JuliusBrussee/caveman/tree/main/plugins/caveman/skills/caveman
- Scope: project-local instructions; this does not register a global skill or install the Caveman proxy, hooks, or other voice modes.

## Multi-tool sync (Codex and Claude Code)

`AGENTS.md`, `.skills/`, and `.reviewers/` are the single source of truth. Never edit `.claude/skills/<name>/` (local skills) or `.claude/agents/` by hand: run `node script/sync-claude.mjs` after changing any source to regenerate them. `CLAUDE.md` imports `AGENTS.md`. The `supabase-server` skill is third-party, installed under `.agents/skills/` and tracked by `skills-lock.json`.
