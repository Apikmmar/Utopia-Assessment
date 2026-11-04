---
name: frontend
description: Build, refactor, and review application interfaces, components, styling, client state, accessibility, and frontend performance across technology stacks. Use for frontend work; pair with the backend skill when shared contracts change.
---

# Frontend engineering

Deliver fast, accessible, secure interfaces whose feature boundaries make changes easy to understand. Apply the shared engineering standards in [AGENTS.md](../../AGENTS.md).

## Establish context

Read the current requirements, applicable documentation, and existing implementation. Identify the target platforms, users, framework, design system, data contracts, and supported devices. Preserve agreed choices and reuse established tooling. If a choice is open, make a proportionate proposal based on the task rather than assuming a particular stack. Apply only relevant guidance; do not introduce features or dependencies merely to satisfy this skill.

## Modular design

- Organize by feature or domain capability. Co-locate a feature's UI, state logic, client operations, validation, and tests as needed. Create files when responsibilities justify them, not to fill a template.
- Keep screens and route components focused on composition. Keep components focused on presentation and interaction; put reusable behavior in focused functions or framework-appropriate state primitives, and transport concerns in a typed client boundary.
- Share established UI primitives and design tokens across features. Keep feature-specific code within its feature and avoid circular imports, cross-feature internals, and catch-all utility files.
- Apply SOLID through component composition and narrow props or service contracts. Introduce an injectable client or adapter when it separates a real dependency; do not wrap every component in an interface.
- Keep server data, form drafts, and transient UI state distinct. Derive values instead of storing redundant copies. Keep state near its consumers and lift it only when sharing is required.
- Treat backend responses as untrusted input at runtime boundaries. Keep transport shapes distinct from view models where their needs differ; prefer generated contract types when the project supports them.

## House structure

When the project follows the house layout (see `zdocumentation/frontend-architecture.md`), keep to it:

- Feature folders under `src/features/<feature>/` with `api.ts` (one function per endpoint), `queries.ts` (TanStack hooks and a key factory: `all`, `lists`, `list(filters)`, `details`, `detail(id)`), `schemas.ts` (Zod for forms and responses), `components/`, `hooks/`, and `pages/`. Shared primitives live in `src/components/ui`, transport in `src/lib`. Features do not import each other's internals.
- kebab-case file names and named exports only.
- One typed API client: relative `/api` base, `credentials: "include"`, Zod-parsed responses, and an `ApiError` with `status`, `code`, `message`, `fields`, and `correlationId` matching the backend error body. Branch on `code`, never on message text.
- Server state through TanStack Query: retry only network errors and 502/503 with a small bound, never retry 4xx or mutations, moderate `staleTime`, and clear the cache when the user changes.
- Forms with React Hook Form and Zod mirror server rules for feedback only and map server `fields` back with `setError`. Keep list filters in the URL. Registries such as role codes are `as const` with a label map and an unknown fallback.

## Code comments

- Add one concise comment directly above each function or method, including function components and custom hooks where applicable. Use language-appropriate comments and limit the entire comment block to two physical lines, including any comment delimiters.
- Explain purpose or non-obvious intent. Place comments only above functions; do not add inline comments, comments inside function bodies, or file and section comment banners.

## Reliable user flows

- Design loading, empty, error, validation, success, and permission-denied states alongside the main screen. Preserve form input when recoverable failures occur.
- Prevent accidental repeated submissions and make pending actions clear. For important mutations, reconcile with the server result; optimistic behavior requires a defined rollback and conflict policy.
- Handle stale requests and component cleanup so late responses cannot overwrite a newer selection. Use the project's data-fetching solution before hand-building caches or request orchestration.
- Keep workflow states and amounts aligned with backend contracts. A client preview is for usability; server calculations and transition results are authoritative.
- Keep frequent user tasks short and clear. Where uploads are required, show progress and recoverable failures, and enforce agreed count and size limits in the UI for feedback.

## Security

- Keep privileged provider keys, infrastructure credentials, and operations requiring secrets in a trusted server environment. Treat anything shipped in client code or browser environment variables as public.
- Use permission-aware UI for usability, while requiring server authorization for every protected operation. Simulated identity or roles must not be presented as real access control.
- Render untrusted content safely using platform-appropriate APIs. For browser rich content, avoid raw HTML injection or use a maintained sanitizer with explicit allowed content. Validate link schemes and navigation targets.
- Follow the selected authentication design and platform security model. Avoid ad hoc credential persistence. For cookie-authenticated browser requests, coordinate CSRF protection; do not assume CORS provides authorization.
- Treat client file checks as feedback only. Handle private files through authorized access, and avoid leaking personal data, credentials, or signed links into logs and analytics.

## Speed and scale

- Fetch only the fields and page of records the screen needs. Use backend search, filtering, sorting, and pagination for growing datasets. Debounce interactive search where useful.
- Reuse server-state caching and invalidation by feature. Scope caches to user and permissions; clear sensitive state when identity changes.
- Avoid request waterfalls when independent work can run concurrently. Split heavy routes or optional modules when bundle evidence justifies it; avoid pulling large packages into common paths.
- Profile before adding memoization, virtualization, or elaborate state machinery. Measure the relevant interaction or bundle change and report the conditions and result.
- Where media is used, bound upload work, release platform resources such as object URLs, and avoid decoding large files unnecessarily. Preserve the required quality of uploaded content.

## Accessibility and verification

- Use platform semantics, visible labels, keyboard or assistive input access, clear focus, readable contrast, and accessible error or progress announcements. Support reduced motion when animation is introduced.
- Check important workflows on their intended devices, input methods, and viewport sizes. Ensure touch targets, forms, navigation, and file controls remain usable where applicable.
- Add or update behavior tests when logic changes: validation, failure recovery, stale responses, permission-aware rendering, or mutation results. Use end-to-end coverage for important user journeys rather than broad snapshot tests.
- Run the project's relevant lint, type, test, and build checks. Visually verify meaningful UI changes when a browser is available; state any unverified interactions.
- Report what changed, relevant verification, performance evidence when claimed, and any backend dependency or remaining limitation.

## Authoritative references

Consult current official documentation for the selected framework, platform, design system, and dependencies when selecting tools or using version-sensitive APIs. Use [OWASP authorization guidance](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html) for relevant access-control concerns.
