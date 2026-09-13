# Fullstack Agentic Flow

Use this file as the top-level instruction set for any user request that may involve backend, frontend, or coordinated full-stack feature delivery.

## Mission

This repository should be treated as a SaaS application foundation designed for:

- fast interview execution
- AI-assisted feature delivery
- predictable architecture growth
- minimal duplication across frontend and backend work

The first responsibility is to route the task correctly before implementation starts.

## Read First

Before developing a feature, read:

- `readme.md`
- `Backend/ARCHITECTURE.md`
- `frontend/ARCHITECTURE.md`
- `.cursor/backend-agentic-flow.md`
- `.cursor/frontend-agentic-flow.md`

## Routing Decision

Classify the request into one of these paths:

1. Backend-only
   Use the backend flow when the task is mainly about APIs, DTOs, services, controllers, migrations, caching, rate limits, integrations, or backend tests.
2. Frontend-only
   Use the frontend flow when the task is mainly about routes, sections, UI states, layout composition, styling, or frontend integration wiring without backend contract changes.
3. Full-stack
   Use both flows when the task changes the API contract and the UI that consumes it.

## Full-Stack Order Of Work

When a feature spans both backend and frontend, follow this order:

1. Ask exactly 3 important clarification questions when the request is ambiguous.
2. Confirm the user flow, API inputs, API outputs, and failure states.
3. Draft a zoomed-out Mermaid architecture diagram of the end-to-end flow before implementation.
4. Add a second focused Mermaid diagram for the specific backend or frontend area being modified when the task is non-trivial.
5. Confirm the freshness and caching expectation for each data touchpoint when stale data could affect trust, auth, or workflow correctness.
6. Decide whether an existing backend module and frontend route pattern can be reused.
7. Define or update backend contracts first.
8. Implement backend behavior and tests.
9. Implement frontend integration against the confirmed backend contract.
10. Add frontend validation states, loading states, and error states.
11. Update documentation in both stacks when structure or flow changes.
12. Verify backend and frontend separately before finishing.

## Clarification Gate

The 3 questions should usually cover:

- the exact user behavior or business flow
- the request and response contract
- key constraints such as auth, persistence, caching, responsiveness, or background work

If the user does not know the exact API shape, recommend one before implementation.

## Reuse Rules

- prefer extending an existing backend domain before creating a new one
- prefer extending an existing frontend route section before creating a new visual pattern
- keep backend business logic in services
- keep frontend presentation logic in reusable sections
- keep integration boundaries explicit between the two stacks
- treat utility routes such as auth, onboarding gates, and setup screens like product workflows, not marketing surfaces
- make cache and freshness rules explicit when data crosses the backend/frontend boundary
- keep secrets and durable auth trust on the backend side whenever the architecture allows it
- when building public-facing SaaS surfaces, prefer predictable high-conversion structure over novelty: clear hero, proof, real product demo, stepwise explanation, pricing/FAQ, and repeated CTA
- for time-boxed app work, avoid placeholder marketing copy and verbose explanatory UI
- when frontend work is involved, prefer practical product UX over decorative layout filler
- when frontend work is involved, design the end-to-end flow first and ensure loading, empty, error, success, and recovery states are part of the feature rather than follow-up polish
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
- frontend lint, typecheck, and build should pass unless blocked
- frontend output should be visually reviewed for hierarchy, spacing, theme alignment, and state completeness
- cache behavior should match data sensitivity, freshness needs, and logout/role-change expectations
- shared docs should reflect the implemented flow
- Mermaid diagrams should be updated when architecture or request flow changed
- Mermaid and Markdown architecture docs should pass the repo-root doc validation commands when they were touched

## Response Rules

- keep updates and final summaries concise
- avoid spending tokens on long explanations unless the user asks for depth
