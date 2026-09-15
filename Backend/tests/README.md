# Project Template Backend — API Testing Framework

A pytest-based testing framework with JSON-driven test cases and module-based organization for the backend template.

## API Endpoints Covered

| Method | Endpoint | Module | Auth |
|--------|----------|--------|------|
| GET | `/` | health | None |
| GET | `/sentry-debug` | health | None |
| POST | `/google-login` | auth | None (Google credential in body) |
| GET | `/verify-token` | auth | Bearer header |
| POST | `/chatbot-response` | chatbot | Bearer header |
| GET | `/all-chats` | chatbot | Bearer header |
| POST | `/stats` | stats | Bearer header |
| GET | `/stats` | stats | Bearer header |
| PUT | `/ticket` | ticket | None |
| GET | `/ticket/{uuid}` | ticket | None |
| GET | `/tickets` | ticket | Bearer header |
| POST | `/ingestion/scrape-website` | ingestion | Bearer header |
| GET | `/ingestion/search` | ingestion | Bearer header |
| POST | `/web-extract/extract-page` | web_extract | None |

## Quick Start

```bash
# 1. Start the backend
cd Backend && ./run.sh

# 2. Refresh auth tokens
python tests/run_tests.py --refresh-tokens

# 3. Run all tests
python tests/run_tests.py

# 4. Mirror backend runtime logs during the test run
TEST_RUNTIME_LOG_PATH=/absolute/path/to/backend-log.txt python tests/run_tests.py web_extract
```

## Test Markers

| Marker | Description |
|--------|-------------|
| `health` | Root / health-check endpoint tests |
| `auth` | Authentication and token verification tests |
| `chatbot` | Chatbot response and chat history tests |
| `ticket` | Support ticket CRUD tests |
| `stats` | Conversation statistics tests |
| `ingestion` | Data scraping, embedding and search tests |
| `web_extract` | Local HTML, Amazon catalog, Playwright, and llms.txt page extraction tests |
| `smoke` | Quick smoke tests for CI/CD |
| `slow` | Slow-running tests (>5 seconds) |
| `external` | Tests requiring external services (Gemini, Pinecone, etc.) |
| `integration` | Full integration tests |

## Test Types

Each test module contains two types of tests:

1. **Parametrized tests** — Driven by JSON case files (`*.cases.json`). Fixtures, inputs, and expected outputs live in JSON. Each entry in the `tests` array becomes a separate pytest test case. Easy to add new scenarios without writing Python code.

2. **Standalone tests** — Written directly in Python for complex assertions, multi-step flows, or edge cases that don't fit the JSON format well.

## Available Assertion Helpers

```python
from helpers.assertions import (
    # Generic
    assert_status_code, assert_field_exists, assert_field_equals,
    assert_field_type, assert_all_fields_present, assert_contains,
    assert_validation_error, assert_not_found_or_error, assert_rate_limited,

    # Chatbot-specific
    assert_chatbot_response,     # Full ChatbotResponse schema check
    assert_booking_response,     # is_booking=true
    assert_handoff_response,     # is_human_handoff=true + ticket_uuid
    assert_regular_response,     # Both flags false

    # Auth-specific
    assert_auth_success, assert_auth_failure, assert_token_verified,

    # Ticket-specific
    assert_ticket_structure, assert_ticket_status,

    # Stats-specific
    assert_stats_structure,
)
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `API_BASE_URL` | `http://localhost:8000` | Backend API URL |
| `API_TIMEOUT` | `30` | Request timeout (seconds) |
| `TEST_MODE` | `local` | Test environment (local/staging/production) |
| `RUN_SLOW_TESTS` | `true` | Whether to run slow tests |
| `RUN_EXTERNAL_TESTS` | `false` | Whether to run tests hitting external services |
| `TEST_AUTH_AUTO_REFRESH` | `false` | Auto-refresh persistent JWTs before tests |
| `TEST_AUTH_SHARED_SECRET` | `` | Shared secret used to call the internal token issuer |
| `TEST_AUTH_REFRESH_ENDPOINT` | `/internal/testing/issue-token` | Internal endpoint used for token refresh |

### Auth Token Setup

Tests that require authentication can either use a manually pasted JWT or auto-refresh tokens through the internal test auth endpoint.

1. Start the backend server
2. Set `ENABLE_INTERNAL_TEST_AUTH=true` and `INTERNAL_SERVICE_SECRET=...` in `Backend/.env`
3. Set matching test env values: `TEST_AUTH_AUTO_REFRESH=true` and `TEST_AUTH_SHARED_SECRET=...`
4. Run `python tests/run_tests.py --refresh-tokens`

If you prefer manual setup, you can still paste a JWT into `persistent-users.json` or run `python tests/run_tests.py --token "YOUR_TOKEN"`.

## Debugging

```bash
pytest tests/usecases/chatbot/test_chatbot.py::test_chatbot_returns_valid_response -v -s
pytest --pdb                    # Drop into debugger on failure
pytest --tb=long                # Full traceback
pytest -vv                      # Extra verbose
python tests/run_tests.py web_extract --server-log /absolute/path/to/backend-log.txt
python tests/run_tests.py web_extract --server-log /absolute/path/to/backend-log.txt --log-filter /web-extract/extract-page
python tests/run_tests.py web_extract --server-log /absolute/path/to/backend-log.txt --unexpected-only
python tests/run_tests.py web_extract --server-log /absolute/path/to/backend-log.txt --fail-on-unexpected-log-status
```

### Runtime Log Mirroring

If you are running the backend in a separate terminal and want the test runner to surface the
server-side request logs, point the runner at that log file:

```bash
export TEST_RUNTIME_LOG_PATH=/absolute/path/to/backend-log.txt
export TEST_RUNTIME_LOG_FILTER=/web-extract/extract-page
export TEST_RUNTIME_LOG_ALLOWED_STATUSES=422
python tests/run_tests.py web_extract
```

The runner snapshots the file before pytest starts, then prints only the new matching log lines
plus an HTTP status summary after the run. For `web_extract`, `422` is treated as expected by
default because the suite includes validation cases that intentionally hit the endpoint with invalid
input.

Use `--unexpected-only` to print only suspicious lines, and `--fail-on-unexpected-log-status` to
turn unexpected mirrored statuses into a failing test run.
