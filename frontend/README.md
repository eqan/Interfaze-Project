# Frontend Template

This frontend is a Next.js App Router and HeroUI workspace baseline for SaaS-style product delivery, protected app flows, and AI-assisted scaling.

## Stack

- Next.js App Router
- HeroUI v3
- Tailwind CSS v4
- TypeScript

Theme mode posture:

- the template ships with a stable default dark theme
- theme toggling is intentionally not enabled in the baseline because the current `next-themes` plus Next 16 dev combination is noisy in local hydration

## Local Setup

```bash
cd frontend
nvm use
npm install
npm run dev
```

Recommended runtime:

- Node `22.22.0` from [`.nvmrc`](/Users/eqanahmad/Desktop/Project-Template/frontend/.nvmrc:1)

## Environment

Copy `.env.example` to `.env.local`:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your-google-oauth-client-id.apps.googleusercontent.com
AUTH_SECRET_KEY=replace-with-a-long-random-secret
AUTH_ALGORITHM=HS256
AUTH_ACCESS_TOKEN_EXPIRE_DAYS=7
GOOGLE_OAUTH_URL=https://oauth2.googleapis.com/tokeninfo
DB_USER=
DB_HOST=
DB_PORT=5432
DB_PASSWORD=
DB_NAME=
INTERFAZE_API_KEY=your-interfaze-api-key
INTERFAZE_MODEL_NAME=interfaze-beta
INTERFAZE_BASE_URL=
INTERFAZE_TIMEOUT_MS=20000
INTERFAZE_RETRY_ATTEMPTS=2
INTERFAZE_RESULT_CACHE_TTL_SECONDS=3600
```

The frontend protects the app behind Google sign-in. `NEXT_PUBLIC_GOOGLE_CLIENT_ID`
must match the Google Identity Services web client configured for the same origins as
the frontend app.

Auth is owned by Next.js:
- `POST /api/auth/google-login` verifies the Google ID token, upserts the shared Postgres `users` row, mints a project JWT, and sets an HttpOnly cookie
- `GET /api/auth/session` verifies the cookie JWT and returns the current user
- `POST /api/auth/logout` clears the cookie
- `POST /api/web-extract/run` forwards page extract requests to FastAPI `POST /web-extract/extract-page` without a JWT. A parent compiler now produces an extraction contract with intent, constraints, expected output, and tool choices. Tools extract JSON, a checker reruns the cycle up to 3 times when confidence is below 0.9 while preserving accepted fields, and low-confidence final results return a structured failure instead of pretending success. The final probability is returned on both `result.confidence` and `meta.confidence`.

`AUTH_SECRET_KEY` must stay server-only. Backend-compatible aliases are also accepted:
`SECRET_KEY`, `ALGORITHM`, and `ACCESS_TOKEN_EXPIRE_DAYS`. Use the same secret value as
backend `SECRET_KEY` when FastAPI domains still verify project JWTs.

`DB_*` connects the frontend auth workflow to the shared Postgres `users` table.

`NEXT_PUBLIC_API_BASE_URL` remains for optional FastAPI domain calls and the page-extract BFF. It is not used for product login or session verification.

`INTERFAZE_API_KEY` is required for the extraction console. The `/api/tasks/run` route
executes the Interfaze workflow inside Next.js instead of proxying document
extraction through the Python backend.

## Commands

```bash
cd frontend
npm run dev
npm run lint
npm run lint:fix
npm run test
npm run typecheck
npm run build
```

## Structure

```text
frontend/
├── app/
│   ├── (app)/
│   ├── (public)/
│   ├── layout.tsx
│   └── providers.tsx
├── components/
├── config/
├── lib/
├── public/
├── styles/
├── ARCHITECTURE.md
└── package.json
```

Route posture:

- `app/(public)`: auth and other non-workspace entry flows
- `app/(app)`: protected routes that share the workspace shell
- `lib/`: runtime helpers and API request boundaries

Main architecture guidance lives in [`ARCHITECTURE.md`](/Users/eqanahmad/Desktop/Project-Template/frontend/ARCHITECTURE.md:1).
