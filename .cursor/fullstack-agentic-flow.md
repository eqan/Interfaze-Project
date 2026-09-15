# Fullstack Agentic Flow

Use this file as the top-level instruction set for any user request that may involve backend, frontend, or coordinated full-stack feature delivery.

## Mission

This repository should be treated as a SaaS application foundation designed for:

- fast interview execution
- AI-assisted feature delivery
- predictable architecture growth
- minimal duplication across frontend and backend work
- deterministic task-platform behavior over template-showcase behavior

The first responsibility is to route the task correctly before implementation starts.

## Read First

Before developing a feature, read:

- `readme.md`
- `backend/ARCHITECTURE.md`
- `frontend/ARCHITECTURE.md`
- `.cursor/backend-agentic-flow.md`
- `.cursor/frontend-agentic-flow.md`

## Routing Decision

Classify the request into one of these paths:

1. Backend-only
   Use the backend flow when the task is mainly about FastAPI domains, DTOs, services, controllers, migrations, backend caching, rate limits, Python integrations, or backend tests.
2. Frontend-only
   Use the frontend flow when the task is mainly about routes, sections, UI states, layout composition, styling, same-origin Next.js API routes, `lib/server` workflows, frontend task contracts, frontend tests, or UI integration against an already-stable backend contract.
3. Full-stack
   Use both flows when the task changes a FastAPI contract and the UI that consumes it, or when durable backend persistence/auth must change alongside a frontend workflow.

Ownership note:

- TypeScript-native operator/AI task execution such as `/api/tasks/run` lives in the frontend stack
- Product Google auth exchange, HttpOnly session cookies, and login-time user persistence live in the frontend stack (`/api/auth/*` + shared Postgres `users` table)
- FastAPI remains the source of truth for existing Python domains and may still verify project JWTs for those routes
- do not route a pure Next.js auth or task-workflow change through backend-first implementation by default

## Full-Stack Order Of Work

When a feature spans both backend and frontend, follow this order:

1. Ask exactly 3 important clarification questions when the request is ambiguous.
2. Confirm the user flow, API inputs, API outputs, and failure states.
3. Draft a zoomed-out Mermaid architecture diagram of the end-to-end flow before implementation.
4. Add a second focused Mermaid diagram for the specific backend or frontend area being modified when the task is non-trivial.
5. Confirm the freshness and caching expectation for each data touchpoint when stale data could affect trust, auth, or workflow correctness.
6. Decide whether an existing backend module, frontend route pattern, or Next.js task workflow can be reused.
7. Choose the owning contract boundary first:
   - FastAPI contract first when durable backend state or an existing Python domain changes
   - frontend task contract first when the workflow is TypeScript-native under `app/api` + `lib/server`
8. Implement the owning stack and its tests.
9. Implement the consuming stack against the confirmed contract.
10. Add frontend validation states, loading states, and error states when UI is involved.
11. Update documentation in both stacks when structure or flow changes.
12. Verify the touched stacks before finishing.

## Clarification Gate

The 3 questions should usually cover:

- the exact user behavior or business flow
- the request and response contract
- key constraints such as auth, persistence, caching, responsiveness, or background work

If the user does not know the exact API shape, recommend one before implementation.

## Reuse Rules

- prefer extending an existing backend domain before creating a new one
- prefer extending an existing frontend route section before creating a new visual pattern
- prefer extending an existing Next.js task route or `lib/server` workflow before adding a Python pass-through for TypeScript-native AI/operator flows
- keep backend business logic in services
- keep frontend presentation logic in reusable sections
- keep frontend server workflow logic in `lib/server`, thin handlers in `app/api`, and browser callers in `lib/api`
- keep integration boundaries explicit between the two stacks
- bias toward one real operator workflow before adding more architecture/demo surfaces
- prefer typed task envelopes, deterministic outputs, idempotency, and observable failure handling when building AI-backed or multi-step product flows
- prefer replacing documentation-heavy route budget with one real operator workflow when the product still lacks a concrete primary task surface
- treat utility routes such as auth, onboarding gates, and setup screens like product workflows, not marketing surfaces
- make cache and freshness rules explicit when data crosses the backend/frontend boundary or a same-origin task route
- keep secrets and durable auth trust on the safest owning side: Next.js server-only modules for product auth cookies and provider keys; FastAPI for Python-domain JWT verification using the shared secret when needed
- when building public-facing SaaS surfaces, prefer predictable high-conversion structure over novelty: clear hero, proof, real product demo, stepwise explanation, pricing/FAQ, and repeated CTA
- for time-boxed app work, avoid placeholder marketing copy and verbose explanatory UI
- when frontend work is involved, prefer practical product UX over decorative layout filler
- when frontend work is involved, design the end-to-end flow first and ensure loading, empty, error, success, and recovery states are part of the feature rather than follow-up polish
- when the likely delivery stack is Next.js and TypeScript, prefer adding or extending a TypeScript-native task boundary before forcing all workflow logic through a Python-first path
- once a screen has cleared the trust and usability baseline, deprioritize extra visual polish in favor of workflow depth, reliability, and test coverage
- before implementing a meaningful change, force a quick systems view first: one zoomed-out diagram for the full flow and one focused diagram for the touched slice when needed

## Pre-Implementation Architecture Sketch

Before implementing non-trivial backend, frontend, or full-stack changes:

- produce a quick Mermaid diagram that shows the zoomed-out architecture or request flow end to end
- also produce a second Mermaid diagram for the particular area being modified: for example the backend request path, frontend route composition, auth flow, cache path, or integration boundary
- keep these diagrams lightweight and decision-oriented; they are meant to clarify the change before code is written, not become large documentation exercises
- if the task is small, one concise focused diagram may be enough, but still reason about the surrounding flow first
- if the change alters the real architecture, promote the sketch into the relevant `ARCHITECTURE.md` or README update in the same task
- use the diagrams to confirm boundaries, dependencies, state transitions, caching decisions, and reuse opportunities before editing code

## Documentation Checks

When a task changes `ARCHITECTURE.md`, `README.md`, other Markdown docs, or Mermaid diagrams:

- update the docs in the same task instead of leaving them for follow-up
- treat Mermaid validity as part of compilation health, not optional polish
- run the repo-root Mermaid checks before finishing:
  `npm run docs:mermaid:check`
- if the fast check fails or the diagrams were edited heavily, also run:
  `npm run docs:mermaid:render`
- use `npm run docs:mermaid:fix` only as a helper, then review the resulting diagrams manually
- apply this doc-validation step whether the task was routed to backend, frontend, or full-stack
- if doc validation cannot be run, say so clearly in the final response

## Handoff To Child Flows

After routing:

- for backend work, follow `.cursor/backend-agentic-flow.md`
- for frontend work, follow `.cursor/frontend-agentic-flow.md`
- for full-stack work, use this file first, then apply both child flows

## Verification

Before finishing a feature:

- backend tests and runtime checks should pass unless blocked
- frontend lint, typecheck, test, and build should pass unless blocked
- frontend output should be visually reviewed for hierarchy, spacing, theme alignment, and state completeness when UI changed
- cache behavior should match data sensitivity, freshness needs, and logout/role-change expectations
- AI-backed flows should have explicit tests for valid output, invalid input, duplicate idempotency keys when relevant, and at least one failure mode such as timeout or provider error
- place those AI/task tests with the owning stack: `frontend/tests/` for Next.js task workflows, `backend/tests/` for FastAPI domains
- shared docs should reflect the implemented flow
- Mermaid diagrams should be updated when architecture or request flow changed
- Mermaid and Markdown architecture docs should pass the repo-root doc validation commands when they were touched

## Response Rules

- keep updates and final summaries concise
- avoid spending tokens on long explanations unless the user asks for depth
