---
name: backend
description: Build, refactor, and review services, business rules, persistence, storage, authorization, and external integrations across technology stacks. Use for backend work; pair with the frontend skill when client contracts change.
---

# Backend engineering

Deliver secure, efficient services with explicit business rules, bounded resource use, and modules that can evolve independently. Apply the shared engineering standards in [AGENTS.md](../../../AGENTS.md).

## Establish context and routing

Read the current requirements, applicable documentation, and existing implementation. Identify the language, runtime, service boundaries, persistence model, security requirements, and deployment constraints. Preserve agreed choices and distinguish open decisions from requirements. Select libraries and providers using current official documentation. Apply only relevant guidance; do not introduce a database, AI integration, or other feature merely to satisfy this skill.

For non-trivial API engineering, follow the available `postman:api-engineer` skill or its directly applicable specialist skill. Inspect existing local contracts and requests before creating replacements. Do not make ordinary implementation depend on publishing to Postman or mutating an external workspace.

## Modular design and SOLID

- Start with a modular monolith organized by business capability. Add transport schemas, services, repositories, and provider adapters within or alongside a feature only where they separate real responsibilities.
- Keep transport handlers responsible for parsing, identity, calling use cases, and mapping results. Keep workflow rules and calculations in services or domain functions. Keep database operations and provider SDK calls in persistence or integration boundaries.
- Use narrow callable, interface, or protocol contracts and dependency injection for replaceable infrastructure, time sources, and external providers where useful. Keep business logic independent of transport objects and concrete SDK clients.
- Prefer composition and small contracts over inheritance hierarchies. Preserve the documented behavior of alternate implementations, including errors and transaction semantics.
- Centralize repeated business rules and policy decisions. Do not build generic CRUD frameworks or universal repositories to remove superficial repetition. Permit direct, simple implementations until a genuine shared concept emerges.
- Expose intentional module entry points. Avoid circular imports and reaching into another feature's private persistence code.

## House structure

When the project follows the house layout (see `zdocumentation/backend-architecture.md`), keep to it rather than inventing a new one:

- `api/main.py` only composes: app factory, middleware, CORS, error handlers, feature routers, and the deny-by-default route check.
- `core/` holds shared infrastructure and cross-feature policy: config, db, logger, request context, middleware, errors, request/response model bases, auth dependencies, crypto, tokens, pagination, and queries several modules share under `core/repository/`. Nothing feature-specific, and `core` never imports `modules`.
- Each feature is one flat module: `router.py`, `service.py`, `repository.py`, `constants.py` only when needed, and `schemas/request.py` plus `schemas/response.py`. Singular module names (`modules/user`); URLs may be plural.
- Routers parse, resolve identity, call one service function, and translate errors. Services hold the rules, own the transaction, and return results or a `ServiceError`; they never import FastAPI or raise HTTP errors. Repositories take an optional connection and run queries only.
- Error codes are UPPER_SNAKE and get their status from one `STATUS_BY_CODE` map. Every error body is `{detail, code}` plus `fields` for validation and `correlationId` for unexpected errors. Add the code to the map before using it.
- JSON fields and query parameters are camelCase through the shared model bases; Python identifiers are camelCase; every module ends with `__all__`.
- A module uses another module only through its service. Shared rules (email normalization, password policy, role codes, session revocation) live once in `core/`, and scripts reuse them instead of copying them.

## Code comments

- Add one concise comment directly above each function or method, above its decorator or annotation block when present. Use language-appropriate line comments and limit the entire comment block to two physical lines.
- Explain purpose or non-obvious intent. Place comments only above functions; do not add inline comments, comments inside function bodies, function docstrings, or file and section comment banners.

## Business correctness and data

- Where behavior includes state transitions, model allowed transitions explicitly and reject invalid changes server-side. Follow documented actor permissions; resolve unspecified actions rather than inventing policy.
- Enforce applicable ownership, tenant, organizational, or resource scopes in authorization and data access. Derive permissions from the current product's requirements rather than assuming particular roles.
- Calculate authoritative values on the server from validated inputs. For money, use decimal arithmetic or integer minor units with an explicit currency and rounding rule. Do not trust client totals.
- When persistence is used, enforce required relationships, uniqueness, and valid values with appropriate datastore constraints. Generate identifiers safely under concurrency rather than reading a current maximum and adding one.
- Commit related business writes atomically, including relevant audit records. Protect state transitions from concurrent updates using an appropriate conditional update, version, or lock. Make retryable completion and other important mutations safe against duplicate effects.
- Store timestamps consistently and define the business timezone and date boundaries used by daily or weekly reports. Aggregate counts and amounts in controlled database queries.
- Use versioned migrations and reproducible seed data. Review migration compatibility and data impact; do not edit a live schema as an undocumented setup step.

## Security boundaries

- Authenticate and authorize protected requests on the server with least privilege and deny-by-default policies. Check access to the actual record or object, not only the route or role name. Filter response fields to avoid exposing internal data.
- If simulated identity is used for development or a demo, keep that mode explicit and prevent it from silently becoming production authentication. Never describe a client-supplied identity as trusted.
- Validate request schemas, allowed fields, lengths, ranges, and enums. Use parameterized queries; do not interpolate untrusted input into SQL, paths, shell commands, or arbitrary database filters.
- Keep secrets in server configuration or a secret manager and validate required settings at startup. Understand whether privileged credentials bypass datastore policies; enforce application authorization and verify any datastore access policies relied upon.
- For browser-facing APIs, restrict origins through explicit CORS configuration and follow the selected authentication design for CSRF protection. Keep error responses useful without exposing stack traces, database details, credentials, or personal data.
- For uploads, enforce ownership, attachment count, byte limits, and allowed types on the server. Verify content beyond filename or declared MIME type, generate storage keys, use private storage with authorized access, and plan cleanup for partially failed uploads.
- Bound expensive endpoints, especially upload and AI work. Apply appropriate request, rate, concurrency, and execution limits; use shared enforcement when running multiple instances.
- When AI is part of the feature, give it only authorized, relevant data from controlled retrieval. Validate model-proposed operations against an allowlist; never execute unrestricted model-generated database commands. Treat model inputs and output as untrusted, and enforce token and cost budgets.

## Speed, resilience, and scale

- Match concurrency to the runtime and libraries in use. Keep blocking database, storage, and provider calls off an async event loop. Use supported async clients or an appropriate execution boundary, with bounded concurrency.
- Reuse clients and bounded connection pools with explicit lifecycle management. Budget total connections across worker processes and deployed instances against database limits.
- Bound result sets and payloads, add deterministic pagination, select needed columns, and avoid N+1 queries. Add indexes for actual filter, join, and sort patterns; inspect query plans when diagnosing slow queries.
- Keep request handlers stateless across instances. Do not rely on process memory for durable jobs, authorization state, idempotency, or global usage limits.
- Set dependency timeouts and bounded retries with backoff only for retry-safe operations. Define partial-failure behavior so a dependency outage does not silently corrupt application state.
- Use durable background jobs or an outbox when delivery must survive a restart. In-process background tasks are suitable only when their loss is acceptable. Distinguish preparing a request or link, accepting work, and confirming delivery according to the actual integration contract.
- Introduce caches only with a measured need, an authorization-aware key, and an invalidation policy. Choose queues or additional services when workload evidence requires them.
- Log structured request identifiers, latency, errors, and relevant audit events without secrets or unnecessary personal data. Measure query count and representative latency when making performance claims; define workload and targets before load testing.

## Contracts and verification

- Keep input, output, error, pagination, and workflow semantics explicit in the API contract. Align browser callers and update affected documentation when the contract changes.
- Test important domain behavior with focused unit tests and persistence behavior with integration tests against the appropriate database. Cover actor or ownership violations, invalid transitions, money calculations, duplicate or concurrent requests, upload limits, and provider failures when affected.
- Use test doubles at external boundaries; verify provider contracts separately when relevant. Do not require paid or live external calls for ordinary tests.
- Run relevant formatting, lint, typing, tests, and migration checks supported by the project. Use targeted API checks for changed endpoints; do not claim mocked tests prove production connectivity.
- Report the change, meaningful verification, deployment or configuration requirements, and any unresolved reliability or security limitations.

## Authoritative references

Consult current official documentation for the selected runtime, framework, datastore, and providers when using version-sensitive integrations. Use [OWASP authorization guidance](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html) for relevant access-control concerns.
