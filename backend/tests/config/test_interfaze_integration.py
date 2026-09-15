import importlib
import importlib.machinery
import sys
import asyncio
from pathlib import Path
import types

import pytest
from fastapi.testclient import TestClient

APP_ROOT = Path(__file__).resolve().parents[2] / "app"
APP_ROOT_STR = str(APP_ROOT)
if APP_ROOT_STR not in sys.path:
    sys.path.insert(0, APP_ROOT_STR)


BACKEND_MODULES_TO_CLEAR = [
    "app",
    "config",
    "config.settings",
    "config.config",
    "dependencies.auth",
    "document_intelligence.documentIntelligenceController",
    "document_intelligence.documentIntelligenceService",
    "document_intelligence.dtos.interfaze",
    "integrations.interfaze_client",
    "utils.cache",
]

BACKEND_NAMESPACE_PACKAGES = [
    "chatbot",
    "config",
    "dependencies",
    "document_intelligence",
    "ingestion",
    "integrations",
    "prompts",
    "stats",
    "ticket",
    "users",
    "utils",
]


def register_backend_namespace_packages():
    for package_name in BACKEND_NAMESPACE_PACKAGES:
        package_path = APP_ROOT / package_name
        if not package_path.is_dir():
            continue

        namespace_package = types.ModuleType(package_name)
        namespace_package.__path__ = [str(package_path)]
        namespace_package.__package__ = package_name
        namespace_package.__spec__ = importlib.machinery.ModuleSpec(
            name=package_name,
            loader=None,
            is_package=True,
        )
        sys.modules[package_name] = namespace_package


def reset_backend_modules():
    while APP_ROOT_STR in sys.path:
        sys.path.remove(APP_ROOT_STR)
    sys.path.insert(0, APP_ROOT_STR)

    for cached in BACKEND_MODULES_TO_CLEAR:
        sys.modules.pop(cached, None)

    register_backend_namespace_packages()


def import_backend_module(module_name: str):
    return importlib.import_module(module_name)


def test_create_app_omits_interfaze_route_when_feature_disabled(monkeypatch):
    reset_backend_modules()
    app_module = import_backend_module("app")
    runtime = app_module.settings.runtime
    runtime.features.enable_scheduler = False
    runtime.features.enable_interfaze = False

    monkeypatch.setattr(app_module.settings, "runtime", runtime, raising=False)
    application = app_module.create_app()
    paths = {route.path for route in application.routes}

    assert "/interfaze/extract-id" not in paths


def test_extract_id_route_returns_structured_response(monkeypatch):
    reset_backend_modules()
    app_module = import_backend_module("app")
    auth_module = import_backend_module("dependencies.auth")
    dto_module = import_backend_module("document_intelligence.dtos.interfaze")
    service_module = import_backend_module("document_intelligence.documentIntelligenceService")

    runtime = app_module.settings.runtime
    runtime.features.enable_scheduler = False
    runtime.features.enable_interfaze = True
    monkeypatch.setattr(app_module.settings, "runtime", runtime, raising=False)

    async def fake_extract_id_details(_payload):
        return dto_module.InterfazeIdExtractionExecution(
            result=dto_module.InterfazeIdExtractionResult(
                first_name="Jane",
                last_name="Doe",
                dob="1994-02-01",
                driver_licence_number="DL-123456",
            ),
            meta=dto_module.InterfazeIdExtractionMeta(
                cached=False,
                idempotency_key="demo-interfaze-key",
            ),
        )

    monkeypatch.setattr(
        service_module.document_intelligence_service,
        "extract_id_details",
        fake_extract_id_details,
    )

    application = app_module.create_app()
    application.dependency_overrides[auth_module.require_authenticated_payload] = (
        lambda: {"sub": "qa-user"}
    )

    with TestClient(application) as client:
        response = client.post(
            "/interfaze/extract-id",
            json={"image_url": "https://example.com/id.jpg"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] is True
    assert body["result"]["first_name"] == "Jane"
    assert body["result"]["driver_licence_number"] == "DL-123456"
    assert body["meta"]["cached"] is False
    assert body["meta"]["idempotency_key"] == "demo-interfaze-key"


def test_extract_id_route_validates_required_fields(monkeypatch):
    reset_backend_modules()
    app_module = import_backend_module("app")
    auth_module = import_backend_module("dependencies.auth")

    runtime = app_module.settings.runtime
    runtime.features.enable_scheduler = False
    runtime.features.enable_interfaze = True
    monkeypatch.setattr(app_module.settings, "runtime", runtime, raising=False)

    application = app_module.create_app()
    application.dependency_overrides[auth_module.require_authenticated_payload] = (
        lambda: {"sub": "qa-user"}
    )

    with TestClient(application) as client:
        response = client.post("/interfaze/extract-id", json={})

    assert response.status_code == 422


def test_extract_id_route_rejects_non_public_urls(monkeypatch):
    reset_backend_modules()
    app_module = import_backend_module("app")
    auth_module = import_backend_module("dependencies.auth")

    runtime = app_module.settings.runtime
    runtime.features.enable_scheduler = False
    runtime.features.enable_interfaze = True
    monkeypatch.setattr(app_module.settings, "runtime", runtime, raising=False)

    application = app_module.create_app()
    application.dependency_overrides[auth_module.require_authenticated_payload] = (
        lambda: {"sub": "qa-user"}
    )

    with TestClient(application) as client:
        response = client.post(
            "/interfaze/extract-id",
            json={"image_url": "http://localhost/id.jpg"},
        )

    assert response.status_code == 422


class FakeCacheService:
    def __init__(self):
        self.store = {}

    def get_json(self, key: str):
        return self.store.get(key)

    def set_json(self, key: str, value, ttl_seconds=None):
        self.store[key] = value


def test_extract_id_service_retries_timeout_then_succeeds(monkeypatch):
    reset_backend_modules()
    dto_module = import_backend_module("document_intelligence.dtos.interfaze")
    service_module = import_backend_module("document_intelligence.documentIntelligenceService")

    fake_cache = FakeCacheService()
    monkeypatch.setattr(service_module, "get_cache_service", lambda: fake_cache)
    monkeypatch.setattr(service_module.settings, "interfaze_timeout_seconds", 1, raising=False)
    monkeypatch.setattr(service_module.settings, "interfaze_retry_attempts", 2, raising=False)

    call_count = {"wait_for": 0, "provider": 0}

    def fake_extract_id_details(*, image_url: str, instruction: str):
        call_count["provider"] += 1
        return dto_module.InterfazeIdExtractionResult(
            first_name="Retry",
            last_name="Success",
            dob="1990-01-01",
            driver_licence_number="DL-RETRY-001",
        )

    async def fake_wait_for(coro, timeout):
        call_count["wait_for"] += 1
        if call_count["wait_for"] == 1:
            coro.close()
            raise TimeoutError
        return await coro

    monkeypatch.setattr(
        service_module.interfaze_client,
        "extract_id_details",
        fake_extract_id_details,
    )
    monkeypatch.setattr(service_module.asyncio, "wait_for", fake_wait_for)

    payload = dto_module.InterfazeIdExtractionRequest(
        image_url="https://example.com/id.jpg",
        instruction="Extract the details from this ID",
        idempotency_key="retry-success-key",
    )

    execution = asyncio.run(
        service_module.document_intelligence_service.extract_id_details(payload)
    )

    assert call_count["wait_for"] == 2
    assert call_count["provider"] == 1
    assert execution.meta.cached is False
    assert execution.meta.idempotency_key == "retry-success-key"
    assert execution.result.first_name == "Retry"
    assert execution.result.driver_licence_number == "DL-RETRY-001"


def test_extract_id_service_maps_provider_failure(monkeypatch):
    reset_backend_modules()
    service_module = import_backend_module("document_intelligence.documentIntelligenceService")
    dto_module = import_backend_module("document_intelligence.dtos.interfaze")

    fake_cache = FakeCacheService()
    monkeypatch.setattr(service_module, "get_cache_service", lambda: fake_cache)
    monkeypatch.setattr(service_module.settings, "interfaze_retry_attempts", 1, raising=False)

    def fake_extract_id_details(*, image_url: str, instruction: str):
        raise RuntimeError("provider offline")

    monkeypatch.setattr(
        service_module.interfaze_client,
        "extract_id_details",
        fake_extract_id_details,
    )

    payload = dto_module.InterfazeIdExtractionRequest(
        image_url="https://example.com/id.jpg",
        instruction="Extract the details from this ID",
        idempotency_key="provider-failure-key",
    )

    with pytest.raises(service_module.HTTPException) as exc_info:
        asyncio.run(service_module.document_intelligence_service.extract_id_details(payload))

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "Interfaze extraction failed"


def test_extract_id_service_reuses_duplicate_idempotency_key(monkeypatch):
    reset_backend_modules()
    dto_module = import_backend_module("document_intelligence.dtos.interfaze")
    service_module = import_backend_module("document_intelligence.documentIntelligenceService")

    fake_cache = FakeCacheService()
    monkeypatch.setattr(service_module, "get_cache_service", lambda: fake_cache)
    monkeypatch.setattr(service_module.settings, "interfaze_retry_attempts", 1, raising=False)

    call_count = {"provider": 0}

    def fake_extract_id_details(*, image_url: str, instruction: str):
        call_count["provider"] += 1
        return dto_module.InterfazeIdExtractionResult(
            first_name="Cache",
            last_name="Hit",
            dob="1988-04-10",
            driver_licence_number="DL-CACHE-123",
        )

    monkeypatch.setattr(
        service_module.interfaze_client,
        "extract_id_details",
        fake_extract_id_details,
    )

    payload = dto_module.InterfazeIdExtractionRequest(
        image_url="https://example.com/id.jpg",
        instruction="Extract the details from this ID",
        idempotency_key="duplicate-run-key",
    )

    first_execution = asyncio.run(
        service_module.document_intelligence_service.extract_id_details(payload)
    )
    second_execution = asyncio.run(
        service_module.document_intelligence_service.extract_id_details(payload)
    )

    assert call_count["provider"] == 1
    assert first_execution.meta.cached is False
    assert second_execution.meta.cached is True
    assert second_execution.meta.idempotency_key == "duplicate-run-key"
    assert second_execution.result.model_dump() == first_execution.result.model_dump()
