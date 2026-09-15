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
    TaskRoute[Next.js task route]
    Backend[FastAPI backend]

    User --> PublicRoutes
    User --> ProtectedRoutes
    ProtectedRoutes --> Shell
    Shell --> Sections
    Sections --> Config
    Sections --> Runtime
    Runtime --> TaskRoute
    TaskRoute --> Backend
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
    participant Guard as AuthGuard
    participant Shell as AppShell
    participant B as FastAPI backend

    U->>P: Request protected route
    alt No auth cookie
        P-->>A: Redirect to /auth
        A->>G: Render sign-in button
        G-->>A: Google credential
        A->>B: POST /google-login
        B-->>A: Project JWT + user
        A->>Provider: Persist auth cookie
    else Auth cookie present
        P-->>Guard: Allow route request
    end
    Guard->>Provider: Read auth cookie
    Provider->>B: GET /verify-token
    B-->>Provider: Verified user payload
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
    participant S as Shared sections
    participant API as lib/api/*
    participant B as Backend

    U->>R: Navigate
    R->>C: Read copy and page maps
    R->>S: Compose cards and panels
    opt Dynamic data
        R->>API: Request typed payload
        API->>T: Call same-origin task route
        T->>B: Proxy typed backend request
        B-->>T: DTO response
        T-->>API: Task response envelope
        API-->>R: Parsed view model
    end
    R-->>U: Render product surface
```

## Task Flow

```mermaid
sequenceDiagram
    participant U as User
    participant C as Extraction console
    participant T as /api/tasks/run
    participant B as FastAPI backend
    participant I as Interfaze route

    U->>C: Submit public image URL + instruction
    C->>T: POST task envelope
    T->>T: Validate task input + auth cookie
    T->>B: POST /interfaze/extract-id
    B->>I: Run typed extraction service
    I-->>B: Result + cache metadata
    B-->>T: Structured DTO response
    T-->>C: Task envelope with status, meta, errors[]
    C-->>U: Success or failure state
```

## Integration Boundary

```mermaid
flowchart TD
    Env[".env.local"]
    ApiBase["NEXT_PUBLIC_API_BASE_URL"]
    GoogleClient["NEXT_PUBLIC_GOOGLE_CLIENT_ID"]
    EnvHelper[lib/env.ts]
    ApiClient[lib/api/client.ts]
    AuthApi[lib/api/auth.ts]
    AuthProvider[components/auth-provider.tsx]
    Routes[Protected routes]
    Backend[FastAPI backend]

    Env --> ApiBase
    Env --> GoogleClient
    ApiBase --> EnvHelper
    GoogleClient --> EnvHelper
    EnvHelper --> ApiClient
    ApiClient --> AuthApi
    AuthApi --> AuthProvider
    AuthProvider --> Routes
    AuthApi --> Backend
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
