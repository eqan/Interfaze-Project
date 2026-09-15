# Backend Architecture

This backend is a FastAPI service with typed settings, service-owned business logic, and a small set of reusable infrastructure pieces. The main module we actively evolved is the web crawler in `app/web_extract/`.

## System Map

```mermaid
flowchart LR
    Client[Client or frontend]
    Router[FastAPI router]
    Service[Backend service]
    Cache[Cache]
    DB[(PostgreSQL)]
    Integrations[Provider adapters]
    WebCrawler[web_extract module]
    Settings[Typed settings]

    Client --> Router
    Router --> Service
    Service --> Cache
    Service --> DB
    Service --> Integrations
    Service --> WebCrawler
    Settings --> Router
    Settings --> Service
    Settings --> Integrations
```

## Core Pattern

- Controllers stay thin.
- Services own orchestration and error handling.
- Integrations are called through adapter modules, not directly from controllers.
- Runtime defaults come from `app/config/runtime.json`.
- Environment-specific values come from `.env`.

## Web Crawler

The crawler accepts a public HTTPS URL and a natural-language prompt, then tries to return deterministic JSON with confidence scoring.

```mermaid
flowchart TD
    Request[URL and user prompt]
    Cache{Cached result?}
    Refiner[LLM prompt refiner]
    Signals[Page signals]
    Planner[Strategy planner]
    Fetch[Fetch HTML]
    Sanitize[Sanitize page text]
    Chunk[Semantic text chunker]
    Regex[Regex evidence]
    ChunkLLM[Chunk extractor]
    Merge[Merge evidence]
    Check{Confidence at least 0.9?}
    Retry[Retry with checker learnings]
    Normalize[Normalize final JSON]
    Success[Return deterministic result]
    LowConfidence[Return low confidence error]

    Request --> Cache
    Cache -->|yes| Success
    Cache -->|no| Refiner
    Refiner --> Signals
    Signals --> Planner
    Planner --> Fetch
    Fetch --> Sanitize
    Sanitize --> Chunk
    Chunk --> Regex
    Chunk --> ChunkLLM
    Regex --> Merge
    ChunkLLM --> Merge
    Merge --> Check
    Check -->|yes| Normalize
    Normalize --> Success
    Check -->|no, attempts left| Retry
    Retry --> Planner
    Check -->|no after 3 tries| LowConfidence
```

### Key Behaviors

- Uses idempotency-key caching for repeat requests.
- Refines short or vague user prompts before planning.
- Builds an extraction contract before collecting evidence.
- Scores output with an LLM-based checker.
- Retries up to 3 times when confidence stays below `0.9`.
- Returns `LOW_CONFIDENCE_EXTRACT` instead of a false success when confidence never reaches the threshold.

## Web Crawler Modules

```mermaid
flowchart TD
    Controller[webExtractController.py]
    Service[webExtractService.py]
    Refiner[input_refiner.py]
    Planner[extract_plan.py]
    Text[plain_text_chunks.py]
    Regex[regex_extractors.py]
    Chunk[chunk_extractor.py]
    Checker[output_checker.py]
    Normalizer[output_normalizer.py]
    Integrations[integrations html and llm adapters]

    Controller --> Service
    Service --> Refiner
    Service --> Planner
    Service --> Text
    Service --> Regex
    Service --> Chunk
    Service --> Checker
    Service --> Normalizer
    Service --> Integrations
```

## Reliability Rules

- Keep request and response DTOs strict.
- Keep provider failures mapped to stable backend errors.
- Prefer deterministic JSON over raw model output.
- Treat caching, retries, and confidence as part of the core contract.
- Add tests whenever planner, checker, or extraction flow changes.

## Verification

Useful checks for this backend area:

- `python -m pytest tests/usecases/web_extract/test_web_extract_service.py`
- `python -m pytest tests/config/test_runtime_contracts.py`
- `npm run docs:mermaid:check`
