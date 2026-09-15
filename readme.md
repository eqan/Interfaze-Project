# Project Template

Full-stack template for fast interview execution, AI-assisted feature work, and predictable scaling. The goal is to keep the base predictable enough that new features can be added quickly without rethinking structure every time.

## Direction

- FastAPI backend with modular domains and typed configuration
- PostgreSQL as the default relational store
- JSON-driven runtime defaults with `.env` overrides per environment
- Cache-ready architecture with in-memory TTL now and Redis-ready abstraction
- Internal test-token refresh flow for stable authenticated test runs
- Interfaze-ready document extraction path in the backend for typed vision parsing demos
- Dynamic Next.js frontend with HeroUI, App Router, and a typed task console

## Current Structure

```text
.
├── Backend/
│   ├── app/
│   │   ├── chatbot/
│   │   ├── config/
│   │   ├── document_intelligence/
│   │   ├── ingestion/
│   │   ├── stats/
│   │   ├── ticket/
│   │   ├── users/
│   │   └── utils/
│   ├── tests/
│   ├── ARCHITECTURE.md
│   ├── main.py
│   ├── run.sh
│   └── pyproject.toml
├── frontend/
│   ├── app/
│   ├── components/
│   ├── config/
│   ├── styles/
│   ├── ARCHITECTURE.md
│   └── package.json
└── readme.md
```

## Backend Principles

- Controllers stay thin and delegate to services.
- Shared infra belongs in `config/`, `database.py`, or `utils/`.
- Template defaults live in `Backend/app/config/runtime.json`.
- Environment-specific values come from `Backend/.env`.
- Optional integrations should degrade gracefully instead of crashing import-time startup.

The main backend reference is [`Backend/ARCHITECTURE.md`](/Users/eqanahmad/Desktop/Project-Template/Backend/ARCHITECTURE.md:1), which is now kept diagram-first with Mermaid flows and minimal prose.

## Frontend Principles

- App Router pages should compose reusable sections instead of one-off layouts.
- HeroUI provides the aesthetic base, while local components define project-specific patterns.
- Frontend environment values belong in `frontend/.env.local`.
- UI should stay aligned with backend DTOs and integration contracts.

The main frontend reference is [`frontend/ARCHITECTURE.md`](/Users/eqanahmad/Desktop/Project-Template/frontend/ARCHITECTURE.md:1).

## Local Setup

### 1. Install dependencies

```bash
cd Backend
uv sync
```

### 2. Configure environment

Copy `Backend/.env.example` to `Backend/.env` and fill in the values you need for your environment.

Important fields:

```env
HOST=0.0.0.0
PORT=8000
RELOAD=false
WORKERS=4
DB_USER=postgres
DB_PASSWORD=change-me
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=interfaze
SECRET_KEY=replace-me
ENABLE_INTERNAL_TEST_AUTH=true
INTERNAL_SERVICE_SECRET=replace-with-a-shared-secret
TEST_AUTH_AUTO_REFRESH=true
TEST_AUTH_SHARED_SECRET=replace-with-the-same-secret
INTERFAZE_API_KEY=replace-with-your-interfaze-key
```

### 3. Start PostgreSQL

Make sure the target database exists and the configured user can connect:

```bash
psql -h 127.0.0.1 -U eqanahmad -d interfaze
```

### 4. Run the backend

```bash
cd Backend
./run.sh
```

Or:

```bash
cd Backend
python main.py
```

### 5. Apply the database schema

Use Alembic to create the current schema in a fresh database:

```bash
cd Backend
alembic upgrade head
```

To generate the SQL without applying it:

```bash
cd Backend
alembic upgrade head --sql
```

### 6. Run the frontend

```bash
cd frontend
nvm use
npm install
npm run dev
```

Frontend environment baseline:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

## Runtime Configuration

`Backend/app/config/runtime.json` contains default operational settings such as:

- server host, port, workers, reload mode
- CORS defaults
- rate limits
- cache backend and TTLs
- feature flags
- DB pool tuning
- AI generation defaults

In practice:

- `runtime.json` is the template baseline
- `.env` is the environment override layer

Use `.env` for values that change by environment, especially:

- secrets
- database credentials
- provider API keys
- internal test auth settings

## Interfaze Readiness

The backend now includes a typed Interfaze-backed demo route for ID parsing:

```text
POST /interfaze/extract-id
```

Request body:

```json
{
  "image_url": "https://r2public.jigsawstack.com/interfaze/examples/id.jpg",
  "instruction": "Extract the details from this ID"
}
```

This route is intended as an interview-ready integration example:

- it is authenticated like other cost-bearing product routes
- it only accepts public `https://` image URLs for safer provider handoff
- it uses a dedicated integration adapter instead of calling the SDK in the controller
- it returns a structured parsed result for the sample ID fields

The frontend now layers a same-origin task route over that backend endpoint:

```text
POST /api/tasks/run
```

Current supported task:

- `extract_id`

This task route gives the product a TypeScript-native execution boundary for:

- request validation
- auth-cookie forwarding
- task metadata and request IDs
- a consistent success/error envelope for the UI

Use `runtime.json` for reusable defaults, especially:

- feature flags
- rate limits
- cache defaults
- server defaults
- AI defaults

## Testing

```bash
cd Backend
python tests/run_tests.py --refresh-tokens
python tests/run_tests.py
```

The test suite is organized by use case and leans on JSON-driven cases so patterns are easy to reproduce. Authenticated tests can auto-refresh JWTs through the internal shared-secret route instead of relying on manual token copy-paste.

If you only want to refresh tokens:

```bash
cd Backend
python tests/run_tests.py --refresh-tokens
```

If you prefer manual token injection:

```bash
cd Backend
python tests/run_tests.py --token "YOUR_JWT_HERE"
```

## Mermaid Doc Validation

Use these commands from the repo root to validate architecture diagrams:

```bash
npm run docs:mermaid:check
npm run docs:mermaid:fix
npm run docs:mermaid:render
```

What they do:

- `docs:mermaid:check`: fast Mermaid lint/validation for markdown files
- `docs:mermaid:fix`: auto-fix common Mermaid syntax issues when possible
- `docs:mermaid:render`: renders each Mermaid block through Mermaid CLI for a stricter final check

## Current Frontend Status

The project now includes a HeroUI-based Next.js frontend baseline designed to evolve into dashboards, product workflows, and backend-driven pages without changing the core structure again.
