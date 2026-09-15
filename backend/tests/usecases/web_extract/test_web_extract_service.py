"""
Focused tests for the contract-driven web extract runtime.
"""

# pyright: reportMissingImports=false

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

APP_ROOT = Path(__file__).resolve().parents[3] / "app"
TESTS_ROOT = Path(__file__).resolve().parents[2]
tests_root_str = str(TESTS_ROOT)
while tests_root_str in sys.path:
    sys.path.remove(tests_root_str)
sys.path.insert(0, str(APP_ROOT))
sys.modules.pop("config", None)
sys.modules.pop("config.settings", None)

from integrations.amazon_creators_client import AmazonCatalogItem  # noqa: E402
from integrations.html_fetcher import HtmlDocument  # noqa: E402
from web_extract.dtos.web_extract import WebExtractRequest  # noqa: E402
from web_extract.extract_plan import ExtractPlan, heuristic_extract_plan, signals_from_url  # noqa: E402
from web_extract.output_checker import OutputCheck, parse_output_check  # noqa: E402
from web_extract.webExtractService import WebExtractContext, WebExtractService  # noqa: E402

if tests_root_str not in sys.path:
    sys.path.insert(0, tests_root_str)

GENERIC_HTML = """
<html>
  <head><title>Example Domain</title></head>
  <body>
    <main id="content">
      <h1>Example Domain</h1>
      <p>This page is for testing the generic extractor.</p>
    </main>
  </body>
</html>
"""

PROFILE_HTML = """
<html>
  <head><title>Eqan Ahmad</title></head>
  <body>
    <main id="profile">
      <h1>Eqan Ahmad</h1>
      <p>AI engineer building web products.</p>
      <a href="https://www.upwork.com/freelancers/~0123456789">Upwork</a>
      <a href="https://github.com/eqanahmad">GitHub</a>
    </main>
  </body>
</html>
"""

AMAZON_URL = "https://www.amazon.com/dp/B0F9PKSJ17"


class FakeCache:
    def __init__(self):
        self.store = {}

    def get_json(self, key: str):
        return self.store.get(key)

    def set_json(self, key: str, value, ttl_seconds: int | None = None) -> None:
        self.store[key] = value


def fake_fetch(html: str):
    def _fetch(url: str) -> HtmlDocument:
        return HtmlDocument(
            url=url,
            final_url=url,
            html=html,
            status_code=200,
            truncated=False,
        )

    return _fetch


def make_context(**overrides) -> WebExtractContext:
    values = {
        "cache": FakeCache(),
        "now": lambda: datetime(2026, 9, 15, 10, 0, tzinfo=timezone.utc),
        "use_browser_fallback": False,
        "use_refine": False,
        "use_regions": False,
        "use_amazon_catalog": False,
        "uuid": lambda: "request-1",
        "plan_job": lambda prompt, signals: heuristic_extract_plan(prompt, signals),
        "normalize_output": lambda _prompt, _url, _expected, data: data,
        "check_output": lambda _prompt, data: OutputCheck(
            confidence=1.0 if data else 0.0,
            missing=(),
            keep=tuple(data.keys()),
        ),
    }
    values.update(overrides)
    return WebExtractContext(**values)


def test_request_rejects_http_and_private_hosts():
    with pytest.raises(ValidationError):
        WebExtractRequest(url="http://example.com", prompt="extract title")
    with pytest.raises(ValidationError):
        WebExtractRequest(url="https://127.0.0.1", prompt="extract title")
    with pytest.raises(ValidationError):
        WebExtractRequest(url="https://example.com", prompt="   ")


def test_output_checker_parses_keep_and_missing_fields():
    check = parse_output_check(
        '{"confidence":0.4,"reason":"missing project","missing":["project"],"keep":["profile"]}'
    )
    assert check.confidence == 0.4
    assert list(check.missing) == ["project"]
    assert list(check.keep) == ["profile"]


def test_generic_chunk_extract_returns_typed_json():
    service = WebExtractService()
    context = make_context(
        fetch_html=fake_fetch(GENERIC_HTML),
        extract_chunk=lambda _prompt, _url, _chunk, _regex, _expected: {"name": "Example Domain"},
    )

    outcome = service.extract_page(
        WebExtractRequest(url="https://example.com", prompt="Extract the page name."),
        context,
    )

    assert outcome.status_code == 200
    assert outcome.body.result is not None
    assert outcome.body.result.data["name"] == "Example Domain"
    assert "chunk_extract" in outcome.body.meta.tools_used
    assert "output_normalizer" in outcome.body.meta.tools_used
    assert "chunks" in outcome.body.meta.provider


def test_prompt_refiner_broadens_request_before_planning():
    service = WebExtractService()
    seen: dict[str, str] = {}

    def plan_job(prompt: str, _signals) -> ExtractPlan:
        seen["plan_prompt"] = prompt
        return ExtractPlan(
            site_type="generic_page",
            intent="extract_structured_data",
            child_prompt=f"Use this brief: {prompt}",
            fields=("name",),
            tools=(),
            expected_output={"name": "<value>"},
        )

    def extract_chunk(prompt: str, _url: str, _chunk: str, _regex: dict, _expected: dict) -> dict:
        seen["child_prompt"] = prompt
        return {"name": "Example Domain"}

    context = make_context(
        fetch_html=fake_fetch(GENERIC_HTML),
        refine_prompt=lambda prompt, _url: (
            "Extract the primary page name from the main content. "
            f"Treat title, heading, or product name as possible synonyms. Original request: {prompt}"
        ),
        plan_job=plan_job,
        extract_chunk=extract_chunk,
    )

    outcome = service.extract_page(
        WebExtractRequest(url="https://example.com", prompt="name"),
        context,
    )

    assert outcome.status_code == 200
    assert seen["plan_prompt"].startswith("Extract the primary page name")
    assert "Original request: name" in seen["plan_prompt"]
    assert "Treat title, heading, or product name as possible synonyms" in seen["child_prompt"]
    assert "prompt_refiner" in outcome.body.meta.tools_used


def test_retry_prompt_reuses_checker_findings():
    service = WebExtractService()
    prompts: list[str] = []
    state = {"n": 0}

    def extract_chunk(prompt: str, _url: str, _chunk: str, _regex: dict, _expected: dict) -> dict:
        prompts.append(prompt)
        if "Accepted findings to keep unchanged" in prompt:
            return {"profile": "Eqan Ahmad", "project": "Project Atlas"}
        return {"profile": "Eqan Ahmad"}

    def check_output(_prompt: str, data: dict) -> OutputCheck:
        state["n"] += 1
        if state["n"] == 1:
            return OutputCheck(
                confidence=0.5,
                reason="missing project",
                missing=("project",),
                keep=("profile",),
            )
        return OutputCheck(confidence=1.0, keep=("profile", "project"))

    context = make_context(
        fetch_html=fake_fetch(GENERIC_HTML),
        extract_chunk=extract_chunk,
        check_output=check_output,
    )
    plan = ExtractPlan(
        site_type="profile_page",
        intent="extract_structured_data",
        child_prompt="Extract profile and project from the page.",
        fields=("profile", "project"),
        tools=(),
        expected_output={"profile": "<value>", "project": "<value>"},
        verification_rules=("return only grounded values",),
    )
    context.plan_job = lambda _prompt, _signals: plan

    outcome = service.extract_page(
        WebExtractRequest(url="https://example.com/profile", prompt="Find the profile and project."),
        context,
    )

    assert outcome.status_code == 200
    assert outcome.body.meta.check_attempts == 2
    retry_prompts = [item for item in prompts if "Accepted findings to keep unchanged" in item]
    assert retry_prompts
    assert '"profile": "Eqan Ahmad"' in retry_prompts[0]
    assert "Fill missing or weak fields: project" in retry_prompts[0]
    assert outcome.body.result is not None
    assert outcome.body.result.data["project"] == "Project Atlas"


def test_low_confidence_extract_fails_after_three_cycles():
    service = WebExtractService()
    state = {"n": 0}

    def check_output(_prompt: str, _data: dict) -> OutputCheck:
        state["n"] += 1
        return OutputCheck(
            confidence=0.4,
            reason="still weak",
            missing=("project",),
            keep=("profile",),
        )

    context = make_context(
        fetch_html=fake_fetch(GENERIC_HTML),
        extract_chunk=lambda _prompt, _url, _chunk, _regex, _expected: {"profile": "Eqan Ahmad"},
        check_output=check_output,
    )
    plan = ExtractPlan(
        site_type="profile_page",
        intent="extract_structured_data",
        child_prompt="Extract profile and project from the page.",
        fields=("profile", "project"),
        tools=(),
        expected_output={"profile": "<value>", "project": "<value>"},
        verification_rules=("project is required",),
    )
    context.plan_job = lambda _prompt, _signals: plan

    outcome = service.extract_page(
        WebExtractRequest(url="https://example.com/profile", prompt="Find the profile and project."),
        context,
    )

    assert outcome.status_code == 422
    assert outcome.body.errors[0].code == "LOW_CONFIDENCE_EXTRACT"
    assert outcome.body.meta.check_attempts == 3
    assert outcome.body.result is not None
    assert outcome.body.result.confidence == 0.4


def test_profile_links_use_contract_regex_and_chunk_pass():
    service = WebExtractService()
    context = make_context(
        fetch_html=fake_fetch(PROFILE_HTML),
        extract_chunk=lambda _prompt, _url, _chunk, _regex, _expected: {
            "profiles": [
                {
                    "platform": "upwork",
                    "url": "https://www.upwork.com/freelancers/~0123456789",
                    "anchorText": "Upwork",
                },
                {
                    "platform": "github",
                    "url": "https://github.com/eqanahmad",
                    "anchorText": "GitHub",
                },
            ]
        },
        normalize_output=lambda _prompt, _url, _expected, _data: {
            "profiles": [
                {
                    "platform": "upwork",
                    "url": "https://www.upwork.com/freelancers/~0123456789",
                    "anchorText": "Upwork",
                },
                {
                    "platform": "github",
                    "url": "https://github.com/eqanahmad",
                    "anchorText": "GitHub",
                },
            ]
        },
    )
    context.plan_job = lambda _prompt, _signals: ExtractPlan(
        site_type="profile_page",
        intent="find_external_profile_links",
        child_prompt="Find outbound Upwork and GitHub profile URLs only.",
        fields=("profiles",),
        tools=(),
        constraints={"samePageOnly": True, "mustBeOutbound": True},
        expected_output={
            "profiles": [
                {"platform": "upwork | github", "url": "https://...", "anchorText": "optional"}
            ]
        },
        verification_rules=("return only requested platform links",),
        regex_rules=(
            {
                "field": "profiles",
                "pattern": r"https?://(?:www\.)?(?:upwork\.com|github\.com)/[^\s\"'<>]+",
                "many": True,
            },
        ),
    )

    outcome = service.extract_page(
        WebExtractRequest(
            url="https://eqanahmad.com",
            prompt="Find my Upwork and GitHub profile links.",
        ),
        context,
    )

    assert outcome.status_code == 200
    assert outcome.body.result is not None
    profiles = outcome.body.result.data["profiles"]
    assert {item["platform"] for item in profiles} == {"upwork", "github"}
    assert "chunk_extract" in outcome.body.meta.tools_used


def test_amazon_catalog_short_circuits_html_fetch():
    service = WebExtractService()
    called = {"html": 0}

    def fetch_html(_url: str) -> HtmlDocument:
        called["html"] += 1
        raise AssertionError("html fetch should not run when catalog seed is sufficient")

    context = make_context(
        fetch_html=fetch_html,
        use_amazon_catalog=True,
        lookup_amazon_item=lambda _asin: AmazonCatalogItem(
            asin="B0F9PKSJ17",
            name="SHARGE 140W Charger",
            price="$94.00",
        ),
    )
    context.plan_job = lambda _prompt, _signals: heuristic_extract_plan(
        "Extract the name and price.", signals_from_url(AMAZON_URL)
    )

    outcome = service.extract_page(
        WebExtractRequest(url=AMAZON_URL, prompt="Extract the name and price."),
        context,
    )

    assert outcome.status_code == 200
    assert called["html"] == 0
    assert outcome.body.result is not None
    assert outcome.body.result.data["name"] == "SHARGE 140W Charger"
    assert outcome.body.result.data["price"] == "$94.00"
