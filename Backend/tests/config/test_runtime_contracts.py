import importlib
import json
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

APP_ROOT = Path(__file__).resolve().parents[2] / "app"
TESTS_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))


def import_backend_module(module_name: str):
    tests_root_str = str(TESTS_ROOT)
    while tests_root_str in sys.path:
        sys.path.remove(tests_root_str)

    app_root_str = str(APP_ROOT)
    while app_root_str in sys.path:
        sys.path.remove(app_root_str)
    sys.path.insert(0, app_root_str)

    sys.modules.pop("config", None)
    sys.modules.pop("config.settings", None)
    sys.modules.pop("config.config", None)
    return importlib.import_module(module_name)


settings_module = import_backend_module("config.settings")
RuntimeSettings = settings_module.RuntimeSettings
Settings = settings_module.Settings


def test_runtime_server_env_overrides_json_defaults(tmp_path, monkeypatch):
    runtime_config = {
        "server": {
            "host": "10.0.0.5",
            "port": 9999,
            "reload": False,
            "workers": 8,
            "timeout_keep_alive": 300,
        }
    }
    runtime_path = tmp_path / "runtime.json"
    runtime_path.write_text(json.dumps(runtime_config), encoding="utf-8")

    monkeypatch.setenv("HOST", "127.0.0.1")
    monkeypatch.setenv("PORT", "8010")
    monkeypatch.setenv("RELOAD", "true")
    monkeypatch.setenv("WORKERS", "2")
    monkeypatch.setenv("TIMEOUT_KEEP_ALIVE", "45")

    settings = Settings(
        db_user="postgres",
        db_name="interfaze",
        secret_key="test-secret",
        runtime_config_path=str(runtime_path),
    )

    assert settings.runtime.server.host == "127.0.0.1"
    assert settings.runtime.server.port == 8010
    assert settings.runtime.server.reload is True
    assert settings.runtime.server.workers == 2
    assert settings.runtime.server.timeout_keep_alive == 45


def test_create_app_omits_disabled_routes(monkeypatch):
    app_module = import_backend_module("app")
    runtime = RuntimeSettings()
    runtime.features.enable_stats = False
    runtime.features.enable_ticketing = False
    runtime.features.enable_ingestion = False
    runtime.features.enable_web_extract = False
    runtime.features.enable_sentry = False

    monkeypatch.setattr(app_module.settings, "runtime", runtime, raising=False)
    application = app_module.create_app()
    paths = {route.path for route in application.routes}

    assert "/stats" not in paths
    assert "/ticket/{uuid}" not in paths
    assert "/tickets" not in paths
    assert "/ingestion/scrape-website" not in paths
    assert "/ingestion/search" not in paths
    assert "/web-extract/extract-page" not in paths
    assert "/sentry-debug" not in paths


def test_google_search_tools_follow_feature_flag(monkeypatch):
    gemini_module = import_backend_module("integrations.gemini_client")
    runtime = RuntimeSettings()
    runtime.features.enable_google_search_grounding = False

    monkeypatch.setattr(gemini_module.settings, "runtime", runtime, raising=False)
    assert gemini_module.gemini_client.google_search_tools() == []

    runtime.features.enable_google_search_grounding = True
    monkeypatch.setattr(gemini_module.settings, "runtime", runtime, raising=False)
    assert gemini_module.gemini_client.google_search_tools() == [{"googleSearch": {}}]


def test_internal_test_auth_dependency_requires_flag(monkeypatch):
    internal_dependency = import_backend_module("dependencies.internal")

    monkeypatch.setattr(internal_dependency.settings, "enable_internal_test_auth", False, raising=False)
    with pytest.raises(HTTPException) as exc_info:
        internal_dependency.require_internal_service_secret("secret")
    assert exc_info.value.status_code == 404

    monkeypatch.setattr(internal_dependency.settings, "enable_internal_test_auth", True, raising=False)
    monkeypatch.setattr(internal_dependency.settings, "internal_service_secret", "expected", raising=False)
    with pytest.raises(HTTPException) as exc_info:
        internal_dependency.require_internal_service_secret("wrong")
    assert exc_info.value.status_code == 401

    assert internal_dependency.require_internal_service_secret("expected") is None
