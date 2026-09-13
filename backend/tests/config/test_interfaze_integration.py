import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient

APP_ROOT = Path(__file__).resolve().parents[2] / "app"
APP_ROOT_STR = str(APP_ROOT)
if APP_ROOT_STR not in sys.path:
    sys.path.insert(0, APP_ROOT_STR)


def import_backend_module(module_name: str):
    while APP_ROOT_STR in sys.path:
        sys.path.remove(APP_ROOT_STR)
    sys.path.insert(0, APP_ROOT_STR)

    for cached in [
        "app",
        "config",
        "config.settings",
        "config.config",
        "dependencies.auth",
        "document_intelligence.documentIntelligenceController",
        "document_intelligence.documentIntelligenceService",
        "document_intelligence.dtos.interfaze",
        "integrations.interfaze_client",
    ]:
        sys.modules.pop(cached, None)

    return importlib.import_module(module_name)


def test_create_app_omits_interfaze_route_when_feature_disabled(monkeypatch):
    app_module = import_backend_module("app")
    runtime = app_module.settings.runtime
    runtime.features.enable_scheduler = False
    runtime.features.enable_interfaze = False

    monkeypatch.setattr(app_module.settings, "runtime", runtime, raising=False)
    application = app_module.create_app()
    paths = {route.path for route in application.routes}

    assert "/interfaze/extract-id" not in paths


def test_extract_id_route_returns_structured_response(monkeypatch):
    app_module = import_backend_module("app")
    auth_module = import_backend_module("dependencies.auth")
    dto_module = import_backend_module("document_intelligence.dtos.interfaze")
    service_module = import_backend_module("document_intelligence.documentIntelligenceService")

    runtime = app_module.settings.runtime
    runtime.features.enable_scheduler = False
    runtime.features.enable_interfaze = True
    monkeypatch.setattr(app_module.settings, "runtime", runtime, raising=False)

    async def fake_extract_id_details(_payload):
        return dto_module.InterfazeIdExtractionResult(
            first_name="Jane",
            last_name="Doe",
            dob="1994-02-01",
            driver_licence_number="DL-123456",
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


def test_extract_id_route_validates_required_fields(monkeypatch):
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
