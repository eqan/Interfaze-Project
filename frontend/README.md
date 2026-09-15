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
INTERFAZE_API_KEY=your-interfaze-api-key
INTERFAZE_MODEL_NAME=interfaze-beta
INTERFAZE_BASE_URL=
INTERFAZE_TIMEOUT_MS=20000
INTERFAZE_RETRY_ATTEMPTS=2
INTERFAZE_RESULT_CACHE_TTL_SECONDS=3600
```

The frontend now protects the app behind Google sign-in. `NEXT_PUBLIC_GOOGLE_CLIENT_ID`
must match the Google Identity Services web client configured for the same origins as
the frontend app.

`NEXT_PUBLIC_API_BASE_URL` should point to the backend origin and should use `https`
outside local development, because frontend auth requests send bearer tokens to that
API boundary.

`INTERFAZE_API_KEY` is required for the extraction console. The `/api/tasks/run` route
now executes the Interfaze workflow inside Next.js instead of proxying document
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
