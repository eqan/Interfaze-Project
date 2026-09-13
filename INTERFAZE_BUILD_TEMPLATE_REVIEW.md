# Interfaze Build Round Review

This note focuses only on the **project-building** portion of your Interfaze prep.

It compares:

- your research notes about the likely build exercise
- the current `Project-Template` structure
- what should be improved so the template feels closer to an Interfaze-style end-to-end build

It intentionally ignores the LeetCode / algorithm section.

## Short Verdict

The template is **directionally strong**, but it still reads more like a **well-structured reusable showcase scaffold** than a **practical deterministic task platform**.

The biggest issues are:

1. the backend posture is still too Python-first for a likely `Next.js + TypeScript + Node` build round
2. the frontend still spends too much route budget on architecture/demo pages instead of one real operator workflow
3. the Interfaze integration proves SDK readiness, but not yet the reliability posture expected in a build exercise

## What Already Matches Well

These parts are already good and should be preserved:

- Clear controller/service separation in the backend
- Typed DTO-driven structure
- Environment and runtime separation with `.env` and `runtime.json`
- Feature-flagged composition
- A protected frontend shell with shared route structure
- A dedicated Interfaze integration boundary instead of SDK calls directly inside controllers

Relevant files:

- [backend/app/app.py](/Users/eqanahmad/Desktop/Project-Template/backend/app/app.py:1)
- [backend/app/config/settings.py](/Users/eqanahmad/Desktop/Project-Template/backend/app/config/settings.py:1)
- [backend/app/config/config.py](/Users/eqanahmad/Desktop/Project-Template/backend/app/config/config.py:1)
- [backend/app/integrations/interfaze_client.py](/Users/eqanahmad/Desktop/Project-Template/backend/app/integrations/interfaze_client.py:1)
- [frontend/app/(app)/layout.tsx](/Users/eqanahmad/Desktop/Project-Template/frontend/app/(app)/layout.tsx:1)
- [frontend/app/(app)/page.tsx](/Users/eqanahmad/Desktop/Project-Template/frontend/app/(app)/page.tsx:1)

## Main Mismatch

Your research suggests the project round is likely to reward:

- `Next.js`
- `React`
- `TypeScript`
- practical end-to-end product building
- deterministic task execution
- reliable failure handling
- structured outputs

The current template is strong architecturally, but the center of gravity is still:

- backend-first
- Python/FastAPI-first
- documentation/demo-surface-heavy in the frontend

That means the template is good for explaining architecture, but slightly less ready for a fast live build in the stack and style they are likely to care about most.

## Priority Improvements

### 1. Add a TypeScript-native backend path

This is the biggest improvement.

Right now, the backend integration story is good, but if the interviewer asks you to build quickly in a `Node/TypeScript` shape, the current template makes you context-switch too much.

Recommended improvement:

- add a lightweight TypeScript API route path inside Next.js, or
- add a small standalone TS service pattern for task execution

Ideal direction:

- `POST /api/tasks/run`
- typed request schema
- typed response envelope
- task-based execution pattern

Why it matters:

- It aligns the template more closely with the likely interview stack.
- It reduces live-coding friction.
- It makes the template feel more like a product platform than a Python template with a frontend attached.

## 2. Replace documentation-first routes with one real workflow

The frontend currently has good structure, but too many routes act as explanation surfaces:

- [frontend/app/(app)/page.tsx](/Users/eqanahmad/Desktop/Project-Template/frontend/app/(app)/page.tsx:1)
- [frontend/app/(app)/architecture/page.tsx](/Users/eqanahmad/Desktop/Project-Template/frontend/app/(app)/architecture/page.tsx:1)
- [frontend/app/(app)/playbook/page.tsx](/Users/eqanahmad/Desktop/Project-Template/frontend/app/(app)/playbook/page.tsx:1)
- [frontend/app/(app)/backend-api/page.tsx](/Users/eqanahmad/Desktop/Project-Template/frontend/app/(app)/backend-api/page.tsx:1)

For the interview, the homepage should do real work.

Recommended replacement:

- input area for a document URL or upload
- submit action
- loading/running state
- structured result display
- error state
- retry or rerun action

The key flow should feel like:

`input -> validate -> execute task -> return structured result -> handle failure cleanly`

That is far more valuable in the interview than multiple polished architecture pages.

## 3. Add a generic task execution contract

The template needs one central contract that says:

- what a task is
- how it is validated
- how it runs
- how it returns success/failure
- how retries and idempotency work

Suggested shape:

```json
{
  "task": "extract_id",
  "input": {},
  "idempotency_key": "optional-string",
  "meta": {},
  "errors": []
}
```

Recommended route:

- `POST /v1/tasks/run`

Why this matters:

- it makes the app feel deterministic and platform-like
- it gives you a reusable pattern for future tasks
- it mirrors how practical AI task systems are usually organized

## 4. Strengthen the Interfaze integration for reliability

The current Interfaze work proves the SDK is integrated, which is good.

Current good pieces:

- dedicated adapter
- typed request/response DTOs
- authenticated route
- public `https` image URL validation

Relevant files:

- [backend/app/document_intelligence/documentIntelligenceController.py](/Users/eqanahmad/Desktop/Project-Template/backend/app/document_intelligence/documentIntelligenceController.py:1)
- [backend/app/document_intelligence/documentIntelligenceService.py](/Users/eqanahmad/Desktop/Project-Template/backend/app/document_intelligence/documentIntelligenceService.py:1)
- [backend/app/document_intelligence/dtos/interfaze.py](/Users/eqanahmad/Desktop/Project-Template/backend/app/document_intelligence/dtos/interfaze.py:1)
- [backend/app/integrations/interfaze_client.py](/Users/eqanahmad/Desktop/Project-Template/backend/app/integrations/interfaze_client.py:1)

What is still missing:

- explicit request timeouts
- retry strategy
- provider error mapping
- idempotency protection
- request IDs / traceable logs
- persistent task record if you want async job posture

This is the difference between “SDK integrated” and “production-minded task system.”

## 5. Make tests reflect failure modes

The best interview-ready tests are not only happy-path tests.

Add focused coverage for:

1. valid extraction request
2. invalid payload
3. provider timeout then retry success
4. provider hard failure
5. duplicate request with same idempotency key

Current test anchor:

- [backend/tests/config/test_interfaze_integration.py](/Users/eqanahmad/Desktop/Project-Template/backend/tests/config/test_interfaze_integration.py:1)

Recommended direction:

- keep the existing route tests
- add task-contract tests
- add service-level failure-mode tests

## 6. Build one end-to-end operator surface

The frontend should look less like “project documentation in app form” and more like “simple internal tool operators can use immediately.”

Recommended primary screen:

### Extraction Console

Sections:

- top summary bar
- document input form
- execution status
- structured extraction result
- recent runs table

Useful components:

- input
- textarea
- button
- status badge
- result card
- table
- retry action

This would immediately make the app feel much closer to the kind of product Interfaze appears to care about.

## What To Deprioritize

These are not useless, but they should not be the focus right now:

- more visual polish on auth/dashboard
- more architecture copy
- more “template explanation” routes
- more aesthetic refinement without workflow depth

You already crossed the minimum bar for visual quality.
The bottleneck now is **practical workflow depth**, not appearance.

## Best Immediate Refactor Plan

If we want the fastest improvement with the highest interview value, the sequence should be:

1. Turn the main protected route into a real Interfaze extraction console
2. Add a generic task contract such as `POST /v1/tasks/run`
3. Add retry, timeout, and idempotency handling
4. Add failure-mode tests
5. Add a TypeScript-native backend route path

## Recommended Final Target

By interview time, the template should ideally feel like this:

- top nav
- one practical product shell
- one real operator workflow
- typed request and response contracts
- deterministic task execution
- visible loading, success, and failure states
- clear provider boundary
- a TypeScript-native path for fast live coding

That would make the project feel much less like a template demo and much more like a credible “mini Interfaze-style platform.”

## Bottom Line

You are not off track.

The template is already organized enough to build on.

But to align better with the project-building section of the Interfaze interview, the next step is not more documentation or design polish.

The next step is to convert the template into a **real task execution product surface**.
