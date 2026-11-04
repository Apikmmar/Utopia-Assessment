---
name: testing
description: Plan, write, run, review, and debug frontend, backend, integration, and end-to-end tests across products and technology stacks. Use for behavior changes needing verification, regression fixes, test setup, and flaky-test diagnosis; scale testing to the change's risk.
---

# Software testing

Build confidence through observable behavior, reproducible failures, and focused tests that survive refactoring. Follow [workspace standards](../../AGENTS.md) and use the [frontend](../frontend/SKILL.md) or [backend](../backend/SKILL.md) skill for the layer under test. Derive expected behavior from the current requirements and applicable documentation. Adapt tools and scenarios to the chosen language, platform, and architecture; do not assume a particular product, stack, or feature set.

## Choose useful coverage

- Inspect existing tests, scripts, contracts, and configuration before adding tooling. Preserve the established runner and conventions. If application code or a test suite is missing, choose tooling when the corresponding application layer exists, using current official documentation.
- Start from requirements and acceptance criteria. Identify the changed behavior, important failure modes, boundary values, and the observable result that proves correctness. Resolve unclear business rules instead of encoding guesses as expected behavior.
- Prefer fast unit tests for domain logic, integration tests for real boundaries, and a small set of end-to-end tests for critical journeys. Choose the lowest layer that can prove each risk; do not enforce an arbitrary test ratio or repeat every case at every layer.
- Cover relevant successful, invalid, unauthorized, empty, boundary, and failure cases. Use equivalence classes and boundary-value analysis instead of exhaustive permutations. Parameterize related scenarios when this improves clarity.
- For a bug fix, reproduce the failure and add a focused regression test when practical. Observe it fail for the original defect before verifying the fix; a setup or import failure does not prove reproduction.
- Add tests for meaningful behavior changes and high-risk logic. Reuse existing checks for low-impact changes; avoid tests that merely repeat source code, inspect wording or file structure, or test framework internals.

## House test layout

When the project follows the house layout:

- Backend tests live in root `tests/` with `pytest.ini` (`pythonpath = backend .`, `testpaths = tests`). Folders set the marker: `tests/unit/<area>` (no database), `tests/integration/api` (app and services), `tests/db` (migrations and tooling). Shared helpers go in `tests/support.py` and fixtures in `tests/conftest.py`.
- Database tests run only with the documented flag (`RUN_DB_TESTS=1`) and each gets a throwaway schema with the migrations applied, dropped afterwards. Never write to the shared `public` schema, and never rely on rolling back a transaction on a shared database to isolate tests.
- Frontend unit and component tests sit next to the code (`*.test.ts(x)`), render real routes against a stubbed fetch at the API client boundary, and share setup from `src/test-support/`. Browser journeys live in `frontend/e2e/`; label mocked-backend journeys as such.

## Write maintainable tests

- Use descriptive names stating the behavior and expected outcome. Keep Arrange, Act, and Assert easy to identify through structure, with one coherent behavior per test. Multiple assertions are appropriate when they prove that behavior.
- Assert public outputs, persisted effects, visible UI, and important absence of side effects. Do not bind tests to private helpers, internal call order, incidental markup, or implementation choices unless they are the contract.
- Derive expected values independently from requirements or explicit fixtures. Do not call the production calculation to generate its own expected answer. Assert meaningful values, not merely a successful status or a non-null result.
- Apply SRP to test cases and helpers. Extract fixtures or builders for established repeated setup, while keeping important scenario inputs visible. Avoid generic test frameworks and heavily parameterized helpers that hide intent.
- Follow the comment rule: add a concise comment only directly above each function or method, above decorators or annotations when present, with a maximum of two physical lines. Use language-appropriate line comments; do not add inline or body comments, function docstrings, or section banners.

## Isolation, fixtures, and test doubles

- Keep tests independent of execution order. Reset dependency overrides, mocks, browser state, environment changes, and created resources during teardown, including after failures.
- Use synthetic data and an isolated test environment. Before tests write, delete, send messages, or incur provider costs, verify the configured target and permitted effects. Do not use production records or credentials as convenient fixtures.
- Control clocks, timezone boundaries, randomness, and generated data when they affect assertions. Freeze time or inject a clock; record random seeds for reproducible generated cases.
- Give parallel workers independent records, schemas, buckets, ports, or other mutable resources as needed. Do not share fixed mutable fixtures across concurrent tests.
- Mock external boundaries rather than the behavior being tested. Keep real domain logic in tests of use cases. Use the actual datastore engine for engine-specific constraints, transactions, locking, and query behavior; a substitute engine or repository mock does not establish those properties.
- Use temporary resources or transaction rollback where appropriate. Exercise actual commits with isolated cleanup when testing cross-connection visibility, concurrency, or background work; wrapping everything in a rollback can hide those behaviors.
- Keep ordinary tests offline and free of paid provider calls. Test doubles must reflect the actual contract, including failures. Verify provider compatibility separately when needed, and label what a mocked result does and does not establish.

## Frontend behavior

- Prefer user interactions and platform accessibility selectors. For browser tests, use accessible roles or labels. Avoid private component state, brittle implementation selectors, and broad snapshots. Use stable test identifiers when accessible selectors cannot identify the element reliably.
- Exercise relevant form validation, pending states, double submissions, stale responses, empty results, error recovery, and preservation of user input. Check permission-aware controls without treating them as authorization enforcement.
- Use condition-based waiting and the runner's waiting assertions. Avoid fixed sleeps and timeout increases that mask races. Capture a trace or screenshot when an interface failure needs diagnosis.
- Verify important flows on their supported devices, viewport sizes, and input methods. Check keyboard or assistive input access, labels, focus movement, and error announcements. Automated accessibility checks complement manual interaction checks.

## Backend and integration behavior

- Exercise request validation, documented status and error bodies, filtering, pagination, and persistence effects through the relevant API boundary. Include application startup and teardown when clients or database resources depend on them.
- Test applicable permissions and ownership: allowed actors succeed, disallowed actors fail, and rejected operations leave protected data unchanged. Include attempts to access another user's or tenant's protected resources. Authentication overrides must not bypass the authorization logic being tested.
- If identity is mocked, label tests as simulated-identity checks. They do not establish production authentication. Verify datastore access policies using the actual identities and privileges they govern; a bypassing administrator credential cannot prove their enforcement.
- Test transactions and concurrent or duplicate writes when affected: identifier uniqueness, valid transitions, atomic related writes, rollback on failure, and no unintended duplicate effects. Coordinate concurrent operations explicitly so the test exercises contention.
- Apply migrations against a disposable database and verify important constraints or data preservation when migrations change. Check rollback only if the migration strategy supports it; do not assume every migration is reversible.
- For endpoint testing, use the available `postman:api-testing` skill when applicable. When exercising an application's HTTP dependency failures against stand-ins, use the available `postman:api-simulation` skill. Reuse contracts and assertions rather than publishing external resources as an unnecessary prerequisite.

## Conditional scenarios

Cover these only when the current feature includes them; derive concrete rules from its requirements:

- State changes and submissions: required inputs, valid transitions, permitted actors, cancellation or retry behavior, and atomic persistence. Reject invalid or repeated operations according to the documented contract.
- Calculations and reporting: independent expected values, precision and rounding, empty inputs, boundaries, aggregation, sorting or ties, and configured timezone or date ranges where relevant.
- Files and media: agreed count and byte limits, exact boundary values, disallowed or mismatched types, ownership, cleanup, and private-file access.
- External integrations and notifications: contract compatibility, timeouts, rate limits, malformed responses, safe retries, duplicate events, and partial failure. Distinguish preparation, acceptance, and confirmed delivery.
- AI features: authorized and bounded retrieval, known source facts, missing data, unsupported requests, malicious input, invalid output, timeout, and usage limits. Assert structured facts and constraints rather than exact prose from a live model.

## Reliability, performance, and CI

- Treat flaky tests as defects. Reproduce and diagnose timing, shared state, cleanup, or infrastructure causes. Retries may collect evidence but must not silently turn intermittent failures into a clean result. Any temporary quarantine needs a reason and follow-up.
- Keep the default suite fast and deterministic; mark integration, browser, provider, and performance checks separately when their setup differs. Configure CI to return nonzero on required test failures or unexpectedly empty test discovery, and retain relevant failure evidence without secrets or customer data.
- Use line and branch coverage to find missing risk coverage, not as proof of correctness. Preserve existing agreed thresholds; do not introduce arbitrary percentages or chase 100% with trivial assertions.
- For performance claims, define workload, dataset, concurrency, environment, latency percentiles, throughput, and acceptable errors before measuring. Separate correctness failures from timing results. Avoid brittle wall-clock assertions in unit tests and do not infer scalability from one successful request.
- Run targeted checks first, then required affected suites. Broaden or repeat only when changes, failures, or unresolved concerns justify it. Do not disable assertions, weaken expectations, or alter requirements merely to obtain a passing run.

## Report evidence

Report the relevant commands, test scope, pass or failure result, and skipped or blocked checks with their reason. Distinguish a product defect from a setup failure or unreliable test, and preserve the shortest useful reproduction. Describe meaningful untested risks without claiming a passing suite proves complete security or correctness.

For skill-only changes, validate the skill and its links; do not claim application tests ran. When application infrastructure is missing, state the gap and complete useful preparation without inventing test results.

## Authoritative references

Consult current official documentation for the selected test runner, UI automation tools, framework, and datastore. Use the tools that fit the current implementation; this skill does not mandate a particular test library or service.
