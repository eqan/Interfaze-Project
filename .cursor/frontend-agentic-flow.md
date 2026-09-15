# Frontend Agentic Flow

Use this file as the frontend child instruction set for any frontend feature, refactor, design update, integration task, or frontend-facing documentation change after task routing has been decided.

Read `.cursor/fullstack-agentic-flow.md` first when the request may involve both frontend and backend changes.

## Mission

This frontend should stay:

- shaped like a real SaaS product, not a demo or landing page
- visually strong out of the box
- easy to extend under interview pressure
- obvious for AI tools to read and continue
- aligned with typed contracts and environment-driven runtime settings
- centered on practical operator workflows rather than documentation-heavy filler surfaces
- able to own same-origin task APIs, server workflows, and frontend tests when the product path is TypeScript-native

## Read First

Before editing frontend behavior, read:

- `frontend/ARCHITECTURE.md`
- `frontend/app/layout.tsx`
- `frontend/app/(app)/page.tsx`
- `frontend/config/site.ts`
- `frontend/styles/globals.css`
- `frontend/README.md`

If changing a specific UI route, also read the route page and any reused section components.

If changing task APIs, server workflows, provider adapters, or frontend tests, also read:

- `frontend/app/api/tasks/run/route.ts`
- `frontend/lib/server/tasks/run-task.ts`
- `frontend/lib/server/interfaze.ts`
- `frontend/lib/server/task-cache.ts`
- `frontend/lib/api/tasks.ts`
- `frontend/types/task.ts`
- `frontend/tests/server/task-run.test.ts`

## Documentation Style

Frontend documentation should be architecture-first and Mermaid-first.

Rules:

- prefer Mermaid diagrams over long prose
- keep text concise and directive
- show route flow, section composition, and integration boundaries
- update diagrams whenever structure or feature flow changes

## Frontend Structure

The frontend is organized around:

- `app/`: UI route pages, layout composition, and same-origin API routes under `app/api/`
- `components/`: reusable visual building blocks
- `config/`: site metadata and reusable content maps
- `lib/api/`: browser/client typed callers for backend or same-origin routes
- `lib/server/`: Next.js server-only workflow logic, provider adapters, caches, and env helpers
- `types/`: shared frontend contracts such as task envelopes and auth shapes
- `styles/`: global visual tokens and theme glue
- `tests/`: Node test runner coverage for server workflows and other non-UI logic

Ownership split:

- FastAPI still owns durable auth exchange, user persistence, and backend domains that live under `backend/`
- Next.js owns TypeScript-native task execution for flows like `/api/tasks/run`, including validation, retries, idempotency cache, and Interfaze provider calls
- Prefer extending the Next.js task boundary for new AI/operator workflows when the stack is already TypeScript-first, instead of forcing every workflow through Python

## Feature Workflow

When asked to add a frontend feature:

1. Ask exactly 3 important clarification questions when the request is ambiguous.
2. Confirm whether the work is UI-only, same-origin task/API work, or both.
3. Confirm the route, actor, and desired interaction flow.
4. Confirm the API inputs, outputs, failure states, and UI states when data or task execution is involved.
5. Reuse an existing route section, API helper, or server workflow pattern when it fits.
6. Create a new section, API route, or server module only when the concept is genuinely separate.
7. Keep server components as the default starting point for pages.
8. Add client components only for interactivity, browser APIs, or local state.
9. Keep App Router handlers thin; put validation, provider calls, retries, and caching in `lib/server/`.
10. Add loading, empty, success, and error states deliberately for UI work.
11. Add or update frontend tests under `frontend/tests/` for server workflows, task contracts, and failure modes.
12. Update docs when structure, patterns, or flows change.
13. Verify with `npm run lint`, `npm run typecheck`, `npm test`, and `npm run build`.

## Project Fit Check

Before designing or changing UI or frontend server behavior:

- scan the existing routes, API handlers, `lib/server` modules, components, tokens, styles, docs, and tests first
- detect the framework, styling system, component patterns, and task-contract patterns before inventing new primitives
- follow the repo's current conventions for copy, icons, accessibility, responsiveness, and typed envelopes
- if design-system rules are missing, infer from the current product surface and keep the inference consistent
- merge any route-specific checklist with these rules instead of replacing it

## Core Stance

- design flows before screens
- build usable product UI, not decorative shells
- solve both the happy path and the state path
- use visual polish in service of clarity, trust, and speed
- treat mobile as its own product constraint, not a desktop layout squeezed smaller
- treat UI copy as product behavior
- commit to an intentional aesthetic direction before styling a new surface
- make interfaces memorable through precision and context-fit, not random novelty

## Design Thinking

Before coding a new page or major component, decide:

- purpose: what user problem this surface solves
- tone: the visual character that fits the product and feature
- constraints: framework, performance, accessibility, responsiveness, and existing system rules
- differentiation: what makes the surface feel intentionally designed rather than templated

Choose one direction and execute it consistently.

## Clarification Gate

The 3 questions should usually cover:

- the exact screen or workflow to build
- whether the contract lives in a Next.js task route, a FastAPI endpoint, or both
- important constraints such as auth, responsiveness, caching, idempotency, retries, or feature flags

If the user is unsure, recommend a concrete screen structure and request/response flow before implementation.

## Server Route And Task Workflow Rules

When the feature needs a same-origin API or AI-backed operator workflow:

- prefer `app/api/**` route handlers as thin HTTP adapters
- put validation, orchestration, retries, timeouts, and caching in `lib/server/`
- keep browser callers in `lib/api/` and shared envelopes in `types/`
- do not scatter provider SDK calls or idempotency logic across page components
- keep secrets and provider config in server-only env helpers such as `lib/server/interfaze-env.ts`
- never expose `INTERFAZE_*` or other server secrets through `NEXT_PUBLIC_*`
- reuse the existing task envelope shape: typed input, structured result, meta, and `errors[]`
- make auth gating explicit in the route or workflow context
- make retry, timeout, cache-hit, invalid-request, and provider-failure behavior explicit and testable
- inject provider/cache/time/uuid dependencies in workflow functions so unit tests can stay deterministic
- call FastAPI only when the feature truly needs backend persistence, auth exchange, or an existing Python domain

Canonical task flow today:

1. UI console submits through `lib/api/tasks.ts`
2. `POST /api/tasks/run` authenticates via auth cookie and delegates
3. `lib/server/tasks/run-task.ts` validates, caches, retries, and executes
4. `lib/server/interfaze.ts` talks to the provider
5. response returns a typed task envelope to the UI

## Testing Rules

Frontend tests live under `frontend/tests/` and run with:

```bash
cd frontend
npm test
```

Rules:

- add tests for new or changed server workflows, task contracts, and reliability behavior
- cover valid success, invalid input, at least one provider failure mode, and idempotent/cached replay when relevant
- prefer testing `lib/server` handlers directly with injected fakes over brittle full-browser setup
- keep tests deterministic: no live provider calls, no wall-clock flakiness, no shared mutable cache leftovers
- colocate by concern, for example `tests/server/` for workflow and provider-adjacent logic
- treat `npm test` as required verification for frontend API/server work, not optional polish

## Design Rules

- preserve one coherent visual language
- prefer reusable sections over one-off layouts
- prefer familiar product patterns over clever layout experiments unless the user explicitly asks for novelty
- avoid generic template filler once the project direction is known
- treat this repository as a SaaS application workspace by default, even when the content is still sparse
- default the primary protected route toward one working operator flow before expanding architecture or playbook-style screens
- for time-boxed product work, avoid marketing copy, explanatory panels, and oversized placeholder content
- prefer minimal task-focused screens that help the user complete the next action fast
- design like a product designer shipping a real app, not a landing-page generator filling empty space
- when route budget is limited, replace architecture/demo copy with one real operator workflow before adding more supporting surfaces
- every screen should have a clear primary action, readable hierarchy, and a reason for each block on the page
- use text sparingly and intentionally; if a paragraph does not help the user decide or act, cut it
- align third-party widgets and embedded controls with the surrounding theme using spacing, framing, contrast, and supporting layout
- prefer strong structure over decorative effects; blur, gradients, and glass should support hierarchy, not replace it
- keep spacing consistent across sections, cards, forms, and actions
- make forms and task flows feel practical: clear labels, obvious next step, short helper text, visible feedback
- prioritize scanability: headings, labels, actions, and key values should be legible within a quick glance
- avoid large dead zones, stretched copy blocks, or cards that exist only to balance composition
- avoid adding UI elements only because the layout feels empty
- keep mobile and desktop layouts intentional
- use HeroUI and local composition, not random dependency sprawl

## Auth Route Rules

- treat login, sign-up, reset, and access-gate routes as utility screens first
- keep auth pages calmer and smaller than in-app workspace surfaces
- use one clear headline, one short supporting explanation, and one obvious primary action
- do not add feature grids, benefit cards, testimonial-style copy, or narrative hero sections to a simple auth route unless the user explicitly asks for them
- if the layout feels too empty, prefer whitespace and stronger hierarchy over adding promotional filler
- third-party auth controls should sit in restrained product chrome so the provider widget feels integrated without competing with the page
- keep auth copy focused on access, verification, return path, and recovery

## UX Rules

- start from the user task, then choose the smallest UI that supports it well
- keep the happy path obvious and reduce competing actions
- error, loading, empty, and success states should feel designed, not appended at the end
- for AI-backed workflows, expose structured results, request status, retry context, and the natural next step directly in the surface
- when the primary workflow is task execution, favor a practical console shape: input, validation, run state, structured result, recovery path, and recent runs when useful
- preserve accessibility basics: contrast, button clarity, focusability, and sensible semantics
- prefer familiar interaction patterns for auth, forms, dashboards, and CRUD unless the user asks for something novel
- if a component looks visually imported from another system, restyle the surrounding container so it feels integrated
- keep domain policy, authorization decisions, and durable workflow state out of presentation components
- keep local interaction state, immediate feedback, and accessibility behavior in the UI layer
- challenge the surface against slow networks, awkward data, repeated actions, and narrow devices when plausible

## Experience Contract

Every flow should clearly include:

- entry point
- user intent and current context
- primary action
- immediate feedback
- outcome
- natural next step or exit

Pattern defaults:

- use hub-and-spoke for dashboards and detail views
- use linear flows for onboarding, setup, and forms
- use tabs only for a few stable top-level areas
- use progressive disclosure when showing everything at once would overload the screen

## Visual Direction

- default product surfaces should feel calm, utilitarian, and high-craft
- favor crisp hierarchy, restrained color, clear affordances, stable layout dimensions, and strong contrast
- use tokens for color, spacing, radius, and motion
- avoid decoration without function
- choose typography deliberately; pair expressive display choices with readable body text when the product allows it
- avoid generic default font choices and repeated one-size-fits-all aesthetic habits
- use dominant colors with controlled accents instead of timid evenly-weighted palettes
- use motion sparingly but intentionally for high-impact moments and feedback
- prefer asymmetry, overlap, density control, or negative space only when they improve hierarchy and memorability
- create atmosphere with backgrounds, texture, borders, or depth only when they reinforce the chosen direction
- avoid generic centered hero layouts when a real product screen is needed
- avoid nested cards and repeated equal-width marketing-card grids as a default pattern
- avoid stock-looking AI visuals or gradients used only to signal "AI"

## Practical SaaS Shell Defaults

For in-app workspace surfaces, dashboards, CRUD flows, settings, docs, and internal product pages:

- default to a familiar top navigation bar for stable top-level product areas
- keep navigation simple: brand on the left, route tabs in the middle when appropriate, account and utility actions on the right
- prefer a compact summary strip or page header under the navbar instead of a persistent left rail by default
- use sidebars only when the information density truly requires them; do not add a left sidebar just to fill space
- let the main content area carry the page purpose while product chrome stays quiet and supportive
- keep layouts content-first: primary task, supporting data, secondary actions
- favor white or near-white surfaces, soft borders, restrained shadows, and one clear accent color for the light theme baseline
- use blue accents in a softer practical range rather than very dark saturated blocks that overpower a light shell
- selected navigation states should use the theme accent itself, with high-contrast text such as white on the active tab
- do not leave dark text on a strong accent background when the selected state becomes harder to read
- keep the visual weight of headers, chips, and tabs aligned with the global theme tokens instead of inventing local colors
- borrow the clarity and familiarity of fast-moving SaaS products like Marc Lou's, but do not copy branding, wording, or identity

## App Shell Vs Public Page

- public marketing or onboarding pages can use stronger storytelling, proof, and conversion structure when the user asks for it
- protected app pages, auth routes, settings, dashboards, and operational tools should bias toward familiarity, speed, and clarity
- when a route behaves like software, prefer product navigation, predictable sections, practical tables/forms, and short copy over hero-style composition

## Predictable SaaS Patterns

For public product pages, onboarding explainers, launch pages, and founder-led SaaS surfaces, prefer a repeatable pattern language inspired by fast-moving indie products such as Marc Lou's:

- start with one sharp headline, one concrete subheading, and one obvious primary CTA
- place proof near the hero: user count, testimonials, customer logos, or a concrete credibility signal
- show the product early with real screenshots, demos, or UI evidence instead of abstract claims
- explain value in ordered steps or a simple progression rather than long paragraphs
- keep sections modular and reusable: hero, proof, demo, how-it-works, feature grid, FAQ, pricing, final CTA
- use short punchy copy that emphasizes outcome, speed, and practicality over technical exposition
- prefer recognizable conversion patterns over experimental layouts when the goal is trust and clarity
- repeat the primary CTA at sensible intervals instead of inventing many competing actions
- make pages feel founder-operated and product-specific through concrete details, not generic startup language
- borrow the structure and clarity, not the exact brand voice, wording, or visual identity
- do not apply this public-page pattern to auth, settings, checkout, admin, or other utility routes unless the user explicitly asks for a marketing treatment

For protected app shells and in-product workspace routes inspired by the same practicality:

- prefer familiar app framing over promotional storytelling
- keep headings concrete and shorter than on public landing pages
- show routes, tables, filters, forms, summaries, results, and next actions early
- make active navigation, account controls, and primary actions immediately obvious
- use practical density: enough information to act, not so much chrome that the shell becomes the main event
- if the layout choice is between expressive and familiar for an operational surface, default to familiar
- after the shell is credible, invest next in workflow clarity and data handling rather than more decorative refinement

## Copy Rules

- avoid filler copy, product-speak, and generic motivational text
- keep headings short and specific
- keep supporting text to one or two useful sentences when possible
- do not explain implementation details in the UI unless the user needs that information to make a decision
- prefer labels and helper text that clarify action, input, or consequence
- name actions specifically instead of using generic labels when possible
- do not expose raw provider errors, stack traces, or internal jargon in user-facing copy
- blame the system, not the user, when recovery is possible

## State Discipline

Every async or data-dependent surface needs:

- loading states that resemble the final layout
- empty states with context and a next step
- error states with plain-language recovery
- success states with lightweight confirmation
- if repeated submissions are plausible, include clear retry, duplicate-run, or cached-result behavior in the flow design

Do not ship a polished happy path with silent failure everywhere else.

## Mobile Rules

- minimum touch target should be 44px
- avoid horizontal overflow at 320px to 375px widths
- do not rely on hover for critical actions
- reserve space for async content to reduce layout jumps
- keep primary actions reachable and forms compact
- consider safe areas for sticky controls

## AI Surface Rules

- make uncertainty visible when an AI feature is actually uncertain
- preserve review, undo, reject, or edit paths when AI output affects trust
- do not fake progress, confidence, or provenance
- keep AI chrome secondary to the user's main task

## Visual Review

Before finishing a frontend change, inspect the output and ask:

- does the page look like one coherent product instead of assembled demo blocks
- is there a strong focal point and a clear next action
- is any text present only to occupy space
- do embedded controls, forms, and widgets visually belong inside the current theme
- are spacing, corner radii, borders, and shadows consistent enough to feel intentional
- does mobile still feel designed, not merely stacked
- are loading, error, empty, and success states visually aligned with the main experience
- is there any section or card that can be removed without hurting usability
- does the flow have a clean exit and recovery path
- are focus, semantics, contrast, and keyboard access still sound
- is every dependency and visual flourish justified

If any answer is weak, revise before finishing.

## Red Flags

Stop and revise when you see:

- happy-path-only UI
- generic or hidden error handling
- hardcoded colors where tokens should exist
- hover-only critical actions
- third-party widgets dropped into the page without visual integration
- oversized copy blocks explaining obvious controls
- animation that slows task completion

## Response Rules

- keep implementation summaries short by default
- report what changed, what was verified, and any blocker
- avoid long frontend explanations unless the user explicitly asks for them

## Data And Integration Rules

- keep backend and same-origin task calls out of leaf presentation components
- centralize browser/client access in `lib/api/`
- centralize server-only workflow logic in `lib/server/`
- keep shared request/response shapes in `types/`
- use `.env.local` for environment-specific frontend settings
- use public env only for browser-safe values such as `NEXT_PUBLIC_API_BASE_URL` and `NEXT_PUBLIC_GOOGLE_CLIENT_ID`
- keep server secrets such as `INTERFAZE_API_KEY` server-only
- align UI view models with the owning contract: FastAPI DTOs for backend domains, frontend task types for `/api/tasks/*`
- validate public runtime values early and fail loudly on unsafe API origins or malformed config
- do not persist bearer tokens, refresh tokens, or other secrets in `localStorage` or `sessionStorage` unless the user explicitly accepts that tradeoff
- treat browser-readable cookies as a weaker baseline than `HttpOnly` backend-managed session cookies
- prefer one source of truth for auth persistence instead of duplicating session data across cookies, storage, and in-memory state
- assume any user-scoped payload can become sensitive once auth, billing, support, or admin features arrive
- when a workflow is TypeScript-native, extend the Next.js task route instead of adding a Python pass-through by default

## Security Baseline

- choose the safest default before adding convenience behavior
- keep tokens, permissions, and durable auth state out of presentation components
- sanitize redirect targets and distrust all return URLs, query params, and provider callback state
- reject malformed or obviously expired auth artifacts before letting the UI treat them as valid
- prefer secure transport assumptions: production API origins should be `https`
- add low-risk response headers when the frontend owns the shell: CSP, frame protections, referrer policy, permissions policy, and content-type protections
- do not expose internal error objects directly to users; map them to short recovery-oriented copy
- challenge every new script, iframe, widget, and remote image against privacy, referrer leakage, and theme fit

## Caching And Freshness

- decide cache strategy from data sensitivity and freshness needs before writing fetch or workflow code
- use `no-store` for auth, session verification, permissions, billing, admin data, one-time tokens, and anything that can become stale or unsafe if replayed
- prefer server or framework cache controls over ad hoc browser storage when the data is not user-authored
- for task workflows, use explicit server-side idempotency/result caches such as `lib/server/task-cache.ts` rather than browser storage
- do not cache personalized API payloads in shared browser storage by default
- use browser storage for drafts, dismissed UI state, recent filters, and other non-secret convenience state only when that persistence helps the user
- document the freshness expectation when adding a new data surface: live, near-live, session-sticky, idempotent-replay, or static
- if the user does not need instant freshness, define an intentional revalidation trigger instead of fetching on every render

## Browser Caching Scenarios

- auth verification, current user, permissions, billing balance, usage quotas:
  use `no-store`; stale values can cause security, trust, or entitlement bugs
- dashboard metrics that should refresh when returning to the page but do not need per-click refetching:
  use a short-lived cache or revalidation trigger on focus/navigation instead of permanent browser storage
- public reference data such as plans, feature descriptions, static docs, or release notes:
  allow framework or browser caching with explicit revalidation because the data is not user-specific
- form drafts, unsent comments, wizard progress, and table filters:
  browser storage is reasonable if the payload is non-secret and the user benefits from resuming work
- search suggestions and frequently reused lookups:
  use in-memory or short-lived cache keyed by query; avoid long-lived persistence unless it materially improves UX
- avatars, logos, and public media:
  let the browser cache the asset, but prefer privacy-safe loading and avoid leaking referrers where possible
- admin screens, support tooling, impersonation flows, and anything that changes authorization context:
  bypass browser caching and clear derived client state aggressively on sign-out or role change
- optimistic UI after a mutation:
  update local view state immediately, then revalidate the authoritative backend response instead of trusting stale cache forever

## Delivery Checklist

Before finishing frontend work, verify:

- clarification happened when the request was ambiguous
- UI-only vs same-origin task/API ownership was chosen deliberately
- route and state flow are clear
- an existing component, API helper, or server workflow pattern was reused when relevant
- new UI works on mobile and desktop
- the screen passes the Visual Review section above when UI changed
- copy is concise and task-focused
- components align with the established theme and spacing system
- server routes stayed thin and workflow logic stayed in `lib/server/`
- task or API changes include tests for success, invalid input, and at least one failure or cache path when relevant
- cache mode matches the surface: auth-sensitive data is fresh, static reference data is not over-fetched, and browser storage is justified
- auth/session persistence does not duplicate secrets across multiple browser storage layers without a deliberate reason
- docs are aligned
- lint, typecheck, test, and build pass unless blocked
