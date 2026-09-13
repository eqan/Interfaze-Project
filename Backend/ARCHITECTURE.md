# Backend Architecture

This backend is a reusable interview-speed template optimized for AI-assisted feature delivery, predictable scaling, and low-friction refactors.

## System Map

```mermaid
flowchart LR
    Client[Client / Frontend / Tests]
    App[FastAPI App]
    Controllers[Controllers]
    Dependencies[Dependencies]
    Services[Services]
    Models[ORM Models]
    DB[(PostgreSQL)]
    Integrations[Integrations]
    Cache[Cache Service]
    Runtime[Typed Runtime Settings]

    Client --> App
    App --> Controllers
    Controllers --> Dependencies
    Controllers --> Services
    Services --> Models
    Models --> DB
    Services --> Integrations
    Services --> Cache
    Runtime --> App
    Runtime --> Controllers
    Runtime --> Services
    Runtime --> Cache
    Runtime --> Integrations
```

## Repo Layout

```mermaid
flowchart TD
    Backend[Backend]
    App[app]
    Tests[tests]
    Alembic[alembic]
    Main[main.py]
    Run[run.sh]
    Arch[ARCHITECTURE.md]

    Backend --> App
    Backend --> Tests
    Backend --> Alembic
    Backend --> Main
    Backend --> Run
    Backend --> Arch

    App --> Chatbot[chatbot]
    App --> Users[users]
    App --> Ticket[ticket]
    App --> Stats[stats]
    App --> DocumentIntelligence[document_intelligence]
    App --> Ingestion[ingestion]
    App --> Config[config]
    App --> Deps[dependencies]
    App --> Integrations[integrations]
    App --> Utils[utils]
    App --> Prompts[prompts]
    App --> Database[database.py]
```

## Request Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant R as Router/Controller
    participant D as Dependency
    participant S as Service
    participant K as Cache
    participant I as Integration
    participant P as PostgreSQL

    C->>R: HTTP request
    R->>R: Validate DTO
    R->>D: Auth / request guard
    D-->>R: Context
    R->>S: Typed request payload
    S->>K: Cache lookup when applicable
    alt Cache hit
        K-->>S: Cached response
    else Cache miss
        S->>P: DB read/write via session_scope()
        S->>I: External provider call if needed
        S->>K: Cache deterministic result
    end
    S-->>R: Structured result
    R-->>C: HTTP response
```

## Startup Flow

```mermaid
flowchart TD
    Main["main.py"] --> AppFactory["app/app.py create_app"]
    AppFactory --> Settings["config/settings.py"]
    Settings --> RuntimeJson["config/runtime.json"]
    Settings --> DotEnv[".env"]
    Settings --> Runtime["RuntimeSettings"]
    Runtime --> Config["config/config.py"]
    Config --> Engine["SQLAlchemy Engine"]
    Config --> Limiter["Rate Limiter"]
    Config --> LazyClients["Lazy Integration Clients"]
    AppFactory --> Routers["Enabled Routers"]
    AppFactory --> Middleware["CORS and lifecycle hooks"]
```

## Configuration Precedence

```mermaid
flowchart LR
    RuntimeJson[runtime.json<br/>template defaults]
    DotEnv[.env<br/>environment overrides]
    Settings[Settings + RuntimeSettings]
    Consumers[App / Services / Cache / Integrations]

    RuntimeJson --> Settings
    DotEnv --> Settings
    Settings --> Consumers
```

Short rule:

- use `runtime.json` for reusable defaults
- use `.env` for environment-specific values and secrets

## Domain Pattern

```mermaid
flowchart TD
    Domain[Domain Module]
    Dto[dtos/]
    Models[models/]
    Controller[domainController.py]
    Service[domainService.py]
    Tests[tests/usecases/domain/]
    Docs[use-case docs]

    Domain --> Dto
    Domain --> Models
    Domain --> Controller
    Domain --> Service
    Controller --> Dto
    Service --> Models
    Tests --> Controller
    Tests --> Service
    Docs --> Domain
```

Current domains:

- `chatbot`: chat generation, SSE, persistence
- `users`: auth exchange, JWT verification, user persistence
- `ticket`: ticket lifecycle
- `stats`: conversation analytics
- `document_intelligence`: typed document extraction flows backed by Interfaze
- `ingestion`: scrape, embed, search

## Feature Flags

```mermaid
flowchart TD
    Flags[settings.runtime.features]
    App[App Composition]
    Services[Service Boundaries]
    Stats[stats router]
    Ticket[ticket router]
    Ingestion[ingestion router]
    Interfaze[interfaze router]
    Scheduler[scheduler startup]
    Sentry[sentry init]
    Grounding[google search grounding]

    Flags --> App
    Flags --> Services
    App --> Stats
    App --> Ticket
    App --> Ingestion
    App --> Interfaze
    App --> Scheduler
    App --> Sentry
    Services --> Grounding
```

Implemented flags in the current codebase:

- `enable_scheduler`
- `enable_stats`
- `enable_ticketing`
- `enable_ingestion`
- `enable_interfaze`
- `enable_sentry`
- `enable_google_search_grounding`

## Runtime Controls

```mermaid
flowchart LR
    Runtime[Runtime Settings]
    Server[server]
    Cors[cors]
    Limits[rate_limits]
    Cache[cache]
    Pool[database_pool]
    AI[ai]
    Features[features]

    Runtime --> Server
    Runtime --> Cors
    Runtime --> Limits
    Runtime --> Cache
    Runtime --> Pool
    Runtime --> AI
    Runtime --> Features
```

## Interfaze Flow

```mermaid
sequenceDiagram
    participant C as Authenticated Client
    participant R as /interfaze/extract-id
    participant D as Auth Dependency
    participant S as documentIntelligenceService
    participant A as interfaze_client adapter
    participant I as Interfaze SDK/API

    C->>R: POST image_url + instruction
    R->>D: Verify JWT
    D-->>R: Auth payload
    R->>S: Typed request DTO
    S->>A: extract_id_details()
    A->>I: chat.completions.parse(...)
    I-->>A: Parsed ID schema
    A-->>S: InterfazeIdExtractionResult
    S-->>R: Structured result
    R-->>C: status + message + result
```

## Caching Strategy

```mermaid
flowchart TD
    Service["Service"]
    CacheAPI["get_cache_service"]
    Backend{"cache backend"}
    Memory["In-memory TTL cache"]
    Redis["Redis cache"]
    Result["Structured response"]

    Service --> CacheAPI
    CacheAPI --> Backend
    Backend --> Memory
    Backend --> Redis
    Memory --> Result
    Redis --> Result
```

Current posture:

- shared cache abstraction in `app/utils/cache.py`
- in-memory TTL by default
- Redis-ready backend path already modeled
- ingestion search already uses the cache layer

## Dependency And Auth Flow

```mermaid
sequenceDiagram
    participant C as Controller
    participant D as app/dependencies/*
    participant U as users/auth logic
    participant S as Service

    C->>D: Require auth dependency
    D->>U: Validate token / extract identity
    U-->>D: User context
    D-->>C: Request context
    C->>S: Invoke business logic
```

## Integration Boundary

```mermaid
flowchart LR
    Services["Services"]
    Adapters["app/integrations/*"]
    Providers["Gemini / DeepSeek / Pinecone / Voyage / Firecrawl / Google / Interfaze"]

    Services --> Adapters
    Adapters --> Providers
```

Rule:

- controllers never call provider SDKs directly

## Schema Change Flow

```mermaid
flowchart TD
    Request[New feature or model change]
    Model[Update ORM model]
    Migration[Add Alembic migration]
    DTO[Adjust DTOs]
    Service[Update service logic]
    Test[Update tests]
    Docs[Update docs]

    Request --> Model
    Model --> Migration
    Migration --> DTO
    DTO --> Service
    Service --> Test
    Test --> Docs
```

## Feature Delivery Flow

```mermaid
flowchart TD
    Ask[Ask 3 clarification questions]
    Contract[Confirm inputs and outputs]
    Sketch[Draft zoomed-out + focused Mermaid flow]
    Reuse{Existing module fits?}
    Existing[Extend existing domain]
    New[Create new domain/use case]
    DTOs[Define strict DTOs]
    Data[Update model + migration if needed]
    Service[Implement service logic]
    Controller[Keep controller thin]
    Ops[Apply cache / rate limit / flags]
    Tests[Add tests in Backend/tests]
    Docs[Document in same area]

    Ask --> Contract
    Contract --> Sketch
    Sketch --> Reuse
    Reuse -->|Yes| Existing
    Reuse -->|No| New
    Existing --> DTOs
    New --> DTOs
    DTOs --> Data
    Data --> Service
    Service --> Controller
    Controller --> Ops
    Ops --> Tests
    Tests --> Docs
```

## Testing Map

```mermaid
flowchart LR
    Usecases["tests/usecases/*"]
    Helpers["tests/helpers/*"]
    ConfigTests["tests/config/*"]
    Endpoints["Endpoint cases"]
    Flows["Multi-step Python flows"]
    Contracts["Runtime/config contracts"]

    Usecases --> Endpoints
    Usecases --> Flows
    Helpers --> Flows
    ConfigTests --> Contracts
```

## Guardrails

```mermaid
flowchart TD
    Good[Preferred]
    Avoid[Avoid]

    Good --> G1[Thin controllers]
    Good --> G2[Strict DTOs]
    Good --> G3[Service-owned logic]
    Good --> G4[Shared dependencies]
    Good --> G5[Typed settings]
    Good --> G6[Shared cache abstraction]
    Good --> G7[Alembic-backed schema changes]

    Avoid --> A1[Direct SDK wiring in controllers]
    Avoid --> A2[Hardcoded env-specific values]
    Avoid --> A3[Duplicated auth logic]
    Avoid --> A4[Ad hoc local caches]
    Avoid --> A5[Silent schema drift]
    Avoid --> A6[Docs drifting away from code]
```
