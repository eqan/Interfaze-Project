# Frontend Architecture

This frontend is now organized as a practical task workspace: public auth stays isolated, protected routes share one shell, and the main route runs one typed operator workflow instead of acting only as a documentation surface.

## System Map

```mermaid
flowchart LR
    User[User]
    PublicRoutes[Public routes]
    ProtectedRoutes[Protected routes]
    Shell[Workspace shell]
    Sections[Route sections]
    Config[Config and content maps]
    Runtime[Runtime and API helpers]
    AuthRoute[Next.js auth routes]
    TaskRoute[Next.js task route]
    TaskServer[Next.js server workflow]
    Interfaze[Interfaze SDK]
    Postgres[Postgres users]
    Backend[FastAPI backend]

    User --> PublicRoutes
    User --> ProtectedRoutes
    ProtectedRoutes --> Shell
    Shell --> Sections
    Sections --> Config
    Sections --> Runtime
    Runtime --> AuthRoute
    AuthRoute --> Postgres
    Runtime --> WebExtractRoute[Next.js web-extract BFF]
    WebExtractRoute --> Backend
    Runtime --> TaskRoute
    TaskRoute --> TaskServer
    TaskServer --> Interfaze
    Runtime --> Backend
```

## Current Layout

```mermaid
flowchart TD
    Frontend[frontend]
    App[app]
    Public["(public)"]
    Protected["(app)"]
    Components[components]
    Config[config]
    Lib[lib]
    Styles[styles]

    Frontend --> App
    Frontend --> Components
    Frontend --> Config
    Frontend --> Lib
    Frontend --> Styles

    App --> Public
    App --> Protected
    App --> RootLayout[layout.tsx]
    Public --> Auth[auth/page.tsx]
    Protected --> Home[page.tsx task console]
    Protected --> Architecture[architecture/page.tsx]
    Protected --> Playbook[playbook/page.tsx]
    Protected --> BackendApi[backend-api/page.tsx]
```

## Route Topology

```mermaid
flowchart LR
    Root[app/layout.tsx]
    PublicLayout["app/(public)/layout.tsx"]
    ProtectedLayout["app/(app)/layout.tsx"]
    AuthGuard[AuthGuard]
    AppShell[AppShell]
    PublicPage["/auth"]
    ProtectedPages["/, /architecture, /playbook, /backend-api"]

    Root --> PublicLayout
    Root --> ProtectedLayout
    PublicLayout --> PublicPage
    ProtectedLayout --> AuthGuard
    AuthGuard --> AppShell
    AppShell --> ProtectedPages
```

## Auth And Shell Flow

```mermaid
sequenceDiagram
    participant U as User
    participant P as Proxy
    participant A as /auth route
    participant G as Google Identity Services
    participant Provider as AuthProvider
    participant Login as /api/auth/google-login
    participant Session as /api/auth/session
    participant DB as Postgres users
    participant Guard as AuthGuard
    participant Shell as AppShell

    U->>P: Request protected route
    alt No auth cookie
        P-->>A: Redirect to /auth
        A->>G: Render sign-in button
        G-->>A: Google credential
        A->>Provider: signInWithGoogleCredential
        Provider->>Login: POST credential
        Login->>Login: Verify Google ID token
        Login->>DB: Upsert user
        Login-->>Provider: user + HttpOnly cookie
    else Auth cookie present
        P-->>Guard: Allow route request
    end
    Guard->>Provider: Bootstrap session
    Provider->>Session: GET session
    Session-->>Provider: Verified user payload
    Provider-->>Shell: Authenticated state
    Shell-->>U: Protected workspace
```

## Rendering Flow

```mermaid
sequenceDiagram
    participant U as User
    participant R as Route page
    participant T as /api/tasks/run
    participant C as Config
    participant Shared as Shared sections
    participant API as lib/api/*
    participant B as Backend
    participant Server as Server workflow

    U->>R: Navigate
    R->>C: Read copy and page maps
    R->>Shared: Compose cards and panels
    opt Dynamic data
        R->>API: Request typed payload
        API->>T: Call same-origin task route
        T->>Server: Run request validation and execution
        Server->>B: Call backend only when the feature needs it
        B-->>Server: DTO response
        Server-->>T: Task response envelope
        T-->>API: Task response envelope
        API-->>R: Parsed view model
    end
    R-->>U: Render product surface
```

## Web Extract Flow

```mermaid
sequenceDiagram
    participant U as User
    participant C as Page extract console
    participant N as /api/web-extract/run
    participant B as FastAPI /web-extract/extract-page
    participant L as Parent planner
    participant E as HTML slicer
    participant Q as LLM output checker

    U->>C: Submit public https URL + prompt
    C->>N: POST same-origin envelope
    N->>B: Forward url + prompt
    alt Cache hit
        B-->>C: Cached JSON, confidence 1.0
    else Fresh extract
        B->>L: Parent compiler: intent, constraints, expected output, child prompt, tools
        L-->>B: Extraction contract
        B->>E: Run selected deterministic tools
        E-->>B: Grounded JSON data + commands
        B->>Q: Score exact output vs user prompt
        alt confidence below 0.9 and attempts under 3
            Q-->>B: Restart extract cycle with missing fields and accepted findings to keep
        else accept
            Q-->>C: JSON plus result.confidence, meta.confidence, and checkAttempts
        else low confidence after 3 tries
            Q-->>C: Structured low-confidence failure with partial data
        end
    else Blocked or empty
        B-->>C: Structured failure envelope
    end
```

## Task Flow

```mermaid
sequenceDiagram
    participant U as User
    participant C as Extraction console
    participant T as /api/tasks/run
    participant S as Next.js server workflow
    participant I as Interfaze SDK

    U->>C: Submit public image URL + instruction
    C->>T: POST task envelope
    T->>T: Validate task input + auth cookie
    T->>S: Validate input + idempotency key
    S->>I: Run typed extraction request
    I-->>S: Structured result
    S-->>T: Result + cache metadata
    T-->>C: Task envelope with status, meta, errors[]
    C-->>U: Success or failure state
```

## Integration Boundary

```mermaid
flowchart TD
    Env[".env.local"]
    ApiBase["NEXT_PUBLIC_API_BASE_URL"]
    GoogleClient["NEXT_PUBLIC_GOOGLE_CLIENT_ID"]
    AuthSecret["AUTH_SECRET_KEY"]
    DbEnv["DB_*"]
    InterfazeEnv["INTERFAZE_*"]
    EnvHelper[lib/env.ts]
    AuthEnv[lib/server/auth-env.ts]
    InterfazeHelper[lib/server/interfaze-env.ts]
    AuthApi[lib/api/auth.ts]
    AuthRoutes["app/api/auth/*"]
    AuthWorkflow["lib/server/auth/session.ts"]
    UsersDb["lib/server/auth/users.ts"]
    TaskRoute["app/api/tasks/run/route.ts"]
    WebExtractRoute["app/api/web-extract/run/route.ts"]
    WebExtractWorkflow["lib/server/web-extract/run.ts"]
    TaskWorkflow["lib/server/tasks/run-task.ts"]
    InterfazeSdk["lib/server/interfaze.ts"]
    AuthProvider[components/auth-provider.tsx]
    Routes[Protected routes]
    Backend[FastAPI backend]
    Postgres[Postgres users]

    Env --> ApiBase
    Env --> GoogleClient
    Env --> AuthSecret
    Env --> DbEnv
    Env --> InterfazeEnv
    ApiBase --> EnvHelper
    GoogleClient --> EnvHelper
    AuthSecret --> AuthEnv
    DbEnv --> AuthEnv
    InterfazeEnv --> InterfazeHelper
    AuthApi --> AuthRoutes
    AuthRoutes --> AuthWorkflow
    AuthEnv --> AuthWorkflow
    AuthWorkflow --> UsersDb
    UsersDb --> Postgres
    AuthApi --> AuthProvider
    AuthProvider --> Routes
    Routes --> TaskRoute
    Routes --> WebExtractRoute
    WebExtractRoute --> WebExtractWorkflow
    WebExtractWorkflow --> Backend
    TaskRoute --> TaskWorkflow
    InterfazeHelper --> TaskWorkflow
    TaskWorkflow --> InterfazeSdk
    EnvHelper --> Backend
```

## Composition Rule

```mermaid
flowchart TD
    Route[Route page]
    Header[PageHeader]
    Cards[InfoCard and custom panels]
    Shell[AppShell frame]
    Helpers[lib helpers]

    Shell --> Route
    Route --> Header
    Route --> Cards
    Route --> Helpers
```

## Guardrails

```mermaid
flowchart TD
    Prefer[Prefer]
    Avoid[Avoid]

    Prefer --> P1[Route groups for access boundaries]
    Prefer --> P2[One shell for protected routes]
    Prefer --> P3[Server-first pages]
    Prefer --> P4[Shared request parsing]
    Prefer --> P5[Reusable section composition]

    Avoid --> A1[Auth UI inside protected shell]
    Avoid --> A2[Fetch logic scattered across leaf components]
    Avoid --> A3[Template hero layouts for product screens]
    Avoid --> A4[Per-page visual systems]
    Avoid --> A5[Docs drifting from real structure]
```
