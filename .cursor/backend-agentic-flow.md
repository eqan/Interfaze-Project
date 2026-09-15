# Backend Agentic Flow

Use this file as the backend child instruction set for any backend feature, bugfix, refactor, infra change, or backend-facing documentation update after task routing has been decided.

Read `.cursor/fullstack-agentic-flow.md` first when the request may involve both backend and frontend changes.

## Mission

This repository is a practical task-platform template designed for:

- fast interview implementation
- AI-assisted feature delivery
- predictable extension patterns
- low-friction scaling from a clean baseline

Optimize for reuse, consistency, and future velocity. Do not solve backend requests with one-off patches if a shared pattern is the better fit.

## Read First

Before editing backend behavior, read these files:

- `backend/ARCHITECTURE.md`
- `backend/app/app.py`
- `backend/app/config/settings.py`
- `backend/app/config/config.py`
- `backend/app/database.py`
- `backend/app/config/runtime.json`
- `backend/tests/README.md`

When changing a specific domain, also read its controller, service, DTOs, models, and tests.

## Documentation Style

Backend documentation should be architecture-first and Mermaid-first.

Rules:

- prefer Mermaid diagrams over long prose explanations
- keep text short and directive
- use flowcharts for system boundaries and request flow
- use sequence diagrams for runtime interactions
- use decision-style diagrams when feature flags or fallbacks matter
- document the real implemented flow, not an aspirational one
- show where DTOs, controllers, services, models, cache, and tests fit
- update diagrams in the same task when the structure or flow changes

## Backend Structure

The backend is organized by domain under `backend/app/`:

- `chatbot/`: chat endpoints, SSE flow, LLM orchestration, chat persistence
- `users/`: Google auth exchange, JWT verification, user persistence
- `ticket/`: ticket creation, updates, retrieval
- `stats/`: conversation analytics and scheduled stat generation
- `ingestion/`: scraping, embedding, vector search, ingestion workflows
- `config/`: typed settings, runtime config, DB engine, limiter, lazy integration clients
- `dependencies/`: shared FastAPI dependencies such as auth helpers
- `integrations/`: provider adapters for Gemini, DeepSeek, Pinecone, Voyage, and Firecrawl
- `utils/`: shared helpers such as caching and payload guards
- `prompts/`: prompt loading and prompt assets
- `database.py`: DB lifecycle helpers including `session_scope()`

When the product direction is AI-assisted workflows or deterministic task execution, prefer modeling the backend like a small task platform rather than a bag of unrelated sample endpoints.

## Source Of Truth

Configuration has two layers:

1. `backend/app/config/runtime.json`
   Template defaults for reusable runtime behavior.
2. `backend/.env`
   Environment-specific overrides for development, staging, and production.

Rules:

- never hardcode secrets, hosts, ports, API keys, or deployment-specific worker settings
- use `.env` for environment-specific values
- use `runtime.json` for template defaults
- if a new operational knob is needed, add it to typed settings or typed runtime config

## App Bootstrap

The canonical startup flow is:

1. `backend/main.py`
2. `backend/app/app.py`
3. `backend/app/config/settings.py`
4. `backend/app/config/config.py`

When changing startup behavior:

- keep `create_app()` as the app-construction boundary
- preserve feature-flag checks at bootstrap time
- avoid import-time crashes from optional integrations
- keep reload and worker behavior deterministic

## Feature Workflow

When asked to add a backend feature:

1. Ask exactly 3 important clarification questions before implementation when the feature request is not fully specified.
2. After those 3 questions, ask for or confirm the API inputs and desired outputs.
3. When helpful, recommend a request/response shape so the user can quickly choose the intended API flow.
4. Identify the most relevant existing domain or use case.
5. Reuse an existing module when it already fits the concept well enough.
6. Create a new domain or use case only when the feature is meaningfully separate.
7. Read the existing flow in the chosen domain before editing.
8. Define strict DTOs and response contracts first.
9. Update persistence shape and Alembic migration if required.
10. Implement business logic in the service layer.
11. Keep controllers thin and delegate to services.
12. Add shared concerns such as caching, idempotency, retries, timeouts, request tracing, feature flags, or runtime config when relevant.
13. Add tests under `backend/tests/`.
14. Document the feature in the same use-case area whenever possible, using Mermaid diagrams as the primary format.
15. Update shared docs if behavior, setup, or architecture changed.

When building multi-step or AI-backed flows, prefer a stable task contract with:

- task identifier
- typed input
- structured output
- meta such as request ID, provider, cached state, or timing
- structured errors

When the expected delivery stack is Next.js and TypeScript, prefer supporting or consuming the frontend-owned task boundary under `frontend/app/api` and `frontend/lib/server` instead of re-implementing the same AI/operator workflow in Python by default.

Create a new domain only when the concept is truly separate from existing ones.

### Clarification Gate

For user-requested backend features, the preferred sequence is:

1. Ask 3 high-signal questions that remove ambiguity.
2. Confirm the API contract by asking for:
   - inputs
   - desired outputs
   - success and failure behavior
3. If the user is unsure, propose a recommended API flow with concrete request and response examples.
4. Only then implement the feature.

The 3 questions should usually cover:

- the exact user or system behavior desired
- the API contract shape
- important constraints such as auth, persistence, background work, caching, or integration needs

## Controller Rules

Controllers should:

- define routes and request/response shapes
- apply shared auth dependencies from `backend/app/dependencies/` when auth is required
- preserve deterministic request/response shapes that frontend and AI tooling can consume safely
- apply rate limits from `settings.runtime.rate_limits`
- delegate to a service
- translate exceptional states into HTTP responses when needed

Controllers should not:

- build SQLAlchemy queries
- instantiate external SDK clients
- hold long orchestration logic
- hardcode configuration values already available in settings

## Service Rules

Services own backend business logic.

Services should:

- encapsulate domain behavior
- call shared infra helpers instead of duplicating setup
- use helper methods for parsing, validation, mapping, and retries
- keep provider-specific logic explicit and localized
- prefer deterministic outputs over raw provider passthroughs
- make retry, timeout, cache-hit, and failure behavior explicit when provider-backed work is involved

For new code:

- prefer `session_scope()` from `backend/app/database.py`
- do not copy older `Session.remove()` boilerplate into new services
- if touching legacy service code, improve local session handling where practical

## Database Rules

Current stack:

- PostgreSQL
- SQLAlchemy ORM
- shared engine in `backend/app/config/config.py`
- `session_scope()` in `backend/app/database.py`

Guidelines:

- keep transactions short
- avoid leaking sessions across method boundaries
- keep ORM models in `<domain>/models/`
- keep DTOs separate from ORM models
- use UTC timestamps for created/updated fields

If schema changes are needed:

- update the ORM model
- add or plan an Alembic migration
- avoid silent schema drift

## Runtime, Cache, And Feature Flags

When adding or changing a backend feature, check whether it needs:

- a feature flag
- a rate-limit setting
- a cache TTL
- a DB pool setting
- a server/runtime setting
- an idempotency or timeout setting

If yes, extend the typed settings rather than scattering raw literals.

Canonical cache entrypoint:

- `backend/app/utils/cache.py`

Current cache posture:

- in-memory TTL cache by default
- Redis-ready abstraction for later scaling

## Integration Rules

Current integrations include:

- Gemini / LLM APIs
- Voyage
- Pinecone
- Firecrawl
- Google OAuth
- Sentry

Rules:

- use provider adapters from `backend/app/integrations/`
- let those adapters rely on lazy client access patterns from `backend/app/config/config.py`
- missing optional credentials should degrade gracefully, not crash startup
- keep provider wiring out of controllers
- if integration complexity grows, extract adapter-style helpers or an `integrations/` module
- map provider failures into stable application errors instead of leaking raw SDK behavior across the app boundary

## API And DTO Rules

- define request/response DTOs in `<domain>/dtos/`
- validate input constraints in Pydantic models
- keep DTOs strict rather than permissive
- keep payload names stable once introduced
- return structured responses that are easy for frontend and AI tooling to consume
- when a workflow is user-triggered and repeatable, include structured metadata and explicit failure semantics

For chatbot work:

- preserve the SSE event contract unless intentionally versioning it
- keep prompt loading centralized through `backend/app/prompts/load_prompt.py`

## Testing Rules

Testing is required for backend changes unless explicitly skipped by the user.

Patterns:

- use JSON-driven test cases for endpoint permutations
- use Python tests for multi-step flows, SSE, auth, and edge cases
- if adding a route, add at least one success-path and one failure-path test
- for AI-backed or provider-backed features, test output shape, invalid input, duplicate idempotency-key behavior when relevant, timeout/retry behavior, and hard failure mapping
- if changing a shared contract, update all affected tests
- prefer documenting the feature in the same use-case folder after tests are added

Test locations:

- `backend/tests/usecases/<domain>/`
- `backend/tests/helpers/`

Documentation location preference:

- first choice: the same use-case folder in `backend/tests/usecases/<domain>/`
- second choice: shared docs such as `backend/tests/README.md`, `backend/ARCHITECTURE.md`, or `readme.md`

## Documentation Rules

When backend behavior changes, update the relevant docs in the same task:

- `readme.md`
- `backend/ARCHITECTURE.md`
- `backend/tests/README.md`
- `backend/.env.example`

The repo should always read like a current template, not an outdated demo artifact.

Documentation should majorly comprise Mermaid diagrams and flow visuals, with minimal supporting text.

## Preferred Vs Legacy Patterns

Prefer for new work:

- `create_app()` bootstrap pattern
- typed settings plus typed runtime config
- `.env` overrides for deployment-specific values
- shared auth dependencies under `backend/app/dependencies/`
- lazy optional clients
- provider adapters under `backend/app/integrations/`
- `session_scope()` for DB lifecycle
- shared cache abstraction
- runtime-sourced rate limits

Avoid expanding these unless intentionally refactoring them:

- duplicated rate-limit literals
- import-time initialization of optional services
- direct session management copied into every method
- backend assumptions tied to the old static widget frontend

## Delivery Checklist

Before finishing backend work, verify:

- 3 clarification questions were asked when the feature was ambiguous
- API inputs and desired outputs were confirmed or explicitly recommended
- an existing domain/module was reused when relevant
- imports still resolve
- settings are typed and documented
- DTOs are strict
- routes remain thin
- services own the logic
- caching/rate limiting/runtime settings were considered where relevant
- tests cover the change
- docs are aligned, including same-folder use-case documentation when appropriate
- Mermaid diagrams were updated when architecture, runtime flow, or request flow changed
- no secrets were added to tracked example files
