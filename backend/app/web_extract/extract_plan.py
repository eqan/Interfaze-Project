from dataclasses import dataclass, field
from urllib.parse import urlparse
import json

from fastapi import HTTPException

from config.settings import settings
from integrations.deepseek_client import deepseek_client
from prompts.load_prompt import load_prompt
from web_extract.amazon_url import extract_amazon_asin
from web_extract.command_planner import CommandPlannerError, _strip_json_fence

AVAILABLE_TOOLS = (
    "amazon_catalog",
    "browser_render",
    "css_seed",
    "llms_txt",
    "link_inventory",
    "region_extract",
    "prompt_windows",
    "css_commands",
)

MAX_CHILD_PROMPT_CHARS = 1_200
MAX_FIELDS = 12
LINK_PLATFORM_HOSTS = {
    "fiverr.com": "fiverr",
    "upwork.com": "upwork",
    "linkedin.com": "linkedin",
    "github.com": "github",
    "contra.com": "contra",
}


@dataclass(frozen=True)
class PageSignals:
    url: str
    host: str = ""
    asin: str | None = None
    title: str = ""
    access_wall: bool = False
    truncated: bool = False
    region_index: str = ""
    available_tools: tuple[str, ...] = AVAILABLE_TOOLS


@dataclass(frozen=True)
class ExtractPlan:
    site_type: str
    child_prompt: str
    fields: tuple[str, ...]
    tools: tuple[str, ...]
    intent: str = "extract_structured_data"
    constraints: dict[str, object] = field(default_factory=dict)
    expected_output: dict[str, object] = field(default_factory=dict)
    verification_rules: tuple[str, ...] = ()
    ids: tuple[str, ...] = ()
    close_url_formats: tuple[str, ...] = ()
    regex_rules: tuple[dict[str, object], ...] = ()
    what_not_to_do: tuple[str, ...] = ()


def signals_from_url(url: str) -> PageSignals:
    parsed = urlparse(url)
    return PageSignals(
        url=url,
        host=(parsed.hostname or "").lower(),
        asin=extract_amazon_asin(url),
    )


def _clean_tools(raw) -> tuple[str, ...]:
    if not isinstance(raw, list):
        return ()
    tools: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            continue
        name = item.strip()
        if name in AVAILABLE_TOOLS and name not in tools:
            tools.append(name)
    return tuple(tools)


def _clean_fields(raw) -> tuple[str, ...]:
    if not isinstance(raw, list):
        return ()
    fields: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            continue
        name = item.strip()
        if name and name not in fields:
            fields.append(name)
        if len(fields) >= MAX_FIELDS:
            break
    return tuple(fields)


def _clean_constraints(raw) -> dict[str, object]:
    if not isinstance(raw, dict):
        return {}
    cleaned: dict[str, object] = {}
    if raw.get("samePageOnly") is True or raw.get("same_page_only") is True:
        cleaned["samePageOnly"] = True
    if raw.get("mustBeOutbound") is True or raw.get("must_be_outbound") is True:
        cleaned["mustBeOutbound"] = True
    domains = raw.get("allowedDomains") or raw.get("allowed_domains") or []
    if isinstance(domains, list):
        kept: list[str] = []
        for item in domains:
            if isinstance(item, str) and item.strip() and item.strip() not in kept:
                kept.append(item.strip().lower())
        if kept:
            cleaned["allowedDomains"] = kept[:12]
    return cleaned


def _clean_expected_output(raw, fallback_fields: tuple[str, ...]) -> dict[str, object]:
    if isinstance(raw, dict) and raw:
        return raw
    if fallback_fields == ("profiles",):
        return {
            "profiles": [
                {
                    "platform": "fiverr | upwork",
                    "url": "https://...",
                    "anchorText": "optional",
                }
            ]
        }
    return {field: "<value>" for field in fallback_fields}


def _clean_verification_rules(raw) -> tuple[str, ...]:
    if not isinstance(raw, list):
        return ()
    rules: list[str] = []
    for item in raw:
        if isinstance(item, str) and item.strip() and item.strip() not in rules:
            rules.append(item.strip())
    return tuple(rules[:12])


def _clean_string_list(raw) -> tuple[str, ...]:
    if not isinstance(raw, list):
        return ()
    values: list[str] = []
    for item in raw:
        if isinstance(item, str) and item.strip() and item.strip() not in values:
            values.append(item.strip())
    return tuple(values[:20])


def _clean_regex_rules(raw) -> tuple[dict[str, object], ...]:
    if not isinstance(raw, list):
        return ()
    rules: list[dict[str, object]] = []
    for item in raw[:20]:
        if not isinstance(item, dict):
            continue
        field_name = item.get("field")
        pattern = item.get("pattern")
        if not isinstance(field_name, str) or not field_name.strip():
            continue
        if not isinstance(pattern, str) or not pattern.strip():
            continue
        rule = {
            "field": field_name.strip(),
            "pattern": pattern.strip()[:300],
            "many": item.get("many") is True,
        }
        rules.append(rule)
    return tuple(rules)


def _link_domains_from_prompt(prompt: str) -> list[str]:
    text = prompt.lower()
    domains: list[str] = []
    for host, platform in LINK_PLATFORM_HOSTS.items():
        if platform in text or host in text:
            domains.append(host)
    return domains


def _site_type(signals: PageSignals) -> str:
    if signals.access_wall:
        return "access_wall"
    if signals.asin:
        return "product_page"
    if "llms.txt" in signals.region_index:
        return "profile_page"
    return "generic_page"


def heuristic_fields(prompt: str) -> tuple[str, ...]:
    prompt_l = prompt.lower()
    if ("link" in prompt_l or "url" in prompt_l) and _link_domains_from_prompt(prompt):
        return ("profiles",)

    fields: list[str] = []
    aliases = (
        (("review", "reviews", "rating"), "reviews"),
        (("spec", "specs", "specification", "feature", "battery"), "specs"),
        (("description", "overview", "summary"), "description"),
        (("project", "projects"), "project"),
        (("profile",), "profile"),
        (("price", "cost", "pricing"), "price"),
        (("title", "heading"), "title"),
        (("product", "name"), "name"),
        (("author",), "author"),
        (("sku", "asin", "model"), "sku"),
    )
    for words, field_name in aliases:
        if any(word in prompt_l for word in words) and field_name not in fields:
            fields.append(field_name)
    return tuple(fields or ("name",))


def _heuristic_contract(prompt: str, signals: PageSignals) -> ExtractPlan:
    prompt_l = prompt.lower()
    site_type = _site_type(signals)
    link_domains = _link_domains_from_prompt(prompt)
    if ("link" in prompt_l or "url" in prompt_l) and link_domains:
        expected_output = {
            "profiles": [
                {
                    "platform": " | ".join(LINK_PLATFORM_HOSTS[domain] for domain in link_domains),
                    "url": "https://...",
                    "anchorText": "optional",
                }
            ]
        }
        return ExtractPlan(
            site_type=site_type if site_type != "generic_page" else "profile_page",
            intent="find_external_profile_links",
            child_prompt=(
                f"{prompt.strip()}\n\n"
                "Return only outbound profile links that match the requested platforms. "
                "Ignore internal anchors, names, project titles, and chrome."
            )[:MAX_CHILD_PROMPT_CHARS],
            fields=("profiles",),
            tools=("link_inventory", "browser_render", "region_extract", "prompt_windows"),
            constraints={
                "samePageOnly": True,
                "mustBeOutbound": True,
                "allowedDomains": link_domains,
            },
            expected_output=expected_output,
            verification_rules=(
                "url host must match an allowed domain",
                "reject internal anchors",
                "reject plain names or project titles",
                "empty profiles is allowed when no matching links exist",
            ),
            close_url_formats=tuple(f"https://{domain}/..." for domain in link_domains),
            regex_rules=(
                {
                    "field": "profiles",
                    "pattern": r"https?://(?:www\.)?(?:"
                    + "|".join(domain.replace(".", r"\.") for domain in link_domains)
                    + r")/[^\s\"'<>]+",
                    "many": True,
                },
            ),
        )

    fields = heuristic_fields(prompt)
    tools: list[str] = ["browser_render", "region_extract", "prompt_windows", "css_commands"]
    if "project" in prompt_l or site_type == "profile_page":
        tools.append("llms_txt")
    if signals.asin:
        tools = ["amazon_catalog", "css_seed", *tools]
    return ExtractPlan(
        site_type=site_type,
        intent="extract_structured_data",
        child_prompt=(
            f"{prompt.strip()}\n\n"
            f"Page type: {site_type}. Active tools: {', '.join(dict.fromkeys(tools))}. "
            f"Fill these fields from grounded page text: {', '.join(fields)}. "
            "Use nested JSON for lists such as reviews or specs. Ignore navigation chrome and access walls."
        )[:MAX_CHILD_PROMPT_CHARS],
        fields=fields,
        tools=tuple(dict.fromkeys(tools)),
        constraints={"samePageOnly": True},
        expected_output=_clean_expected_output({}, fields),
        verification_rules=("returned values must be grounded in the page",),
        regex_rules=(
            (
                {"field": "price", "pattern": r"\$\d+(?:\.\d{2})?", "many": False},
            )
            if "price" in fields
            else ()
        ),
    )


def heuristic_extract_plan(prompt: str, signals: PageSignals) -> ExtractPlan:
    return _heuristic_contract(prompt, signals)


def plan_from_mapping(raw: dict, prompt: str, signals: PageSignals | None = None) -> ExtractPlan:
    fallback = heuristic_extract_plan(prompt, signals or signals_from_url("https://example.com"))
    child = raw.get("childPrompt") or raw.get("child_prompt") or fallback.child_prompt
    site_type = raw.get("siteType") or raw.get("site_type") or fallback.site_type
    intent = raw.get("intent") or fallback.intent
    if not isinstance(child, str) or not child.strip():
        child = fallback.child_prompt
    if not isinstance(site_type, str) or not site_type.strip():
        site_type = fallback.site_type
    if not isinstance(intent, str) or not intent.strip():
        intent = fallback.intent
    tools = _clean_tools(raw.get("tools")) or fallback.tools
    fields = _clean_fields(raw.get("fields")) or fallback.fields
    constraints = _clean_constraints(raw.get("constraints")) or fallback.constraints
    expected_output = _clean_expected_output(
        raw.get("expectedOutput") or raw.get("expected_output"),
        fields,
    )
    verification_rules = _clean_verification_rules(
        raw.get("verificationRules") or raw.get("verification_rules")
    ) or fallback.verification_rules
    ids = _clean_string_list(raw.get("ids"))
    close_url_formats = _clean_string_list(
        raw.get("closeUrlFormats") or raw.get("close_url_formats")
    ) or fallback.close_url_formats
    regex_rules = _clean_regex_rules(raw.get("regexes") or raw.get("regex_rules")) or fallback.regex_rules
    what_not_to_do = _clean_string_list(
        raw.get("whatNotToDo") or raw.get("what_not_to_do")
    )
    return ExtractPlan(
        site_type=site_type.strip()[:64],
        intent=intent.strip()[:64],
        child_prompt=child.strip()[:MAX_CHILD_PROMPT_CHARS],
        fields=fields,
        tools=tools,
        constraints=constraints,
        expected_output=expected_output,
        verification_rules=verification_rules,
        ids=ids,
        close_url_formats=close_url_formats,
        regex_rules=regex_rules,
        what_not_to_do=what_not_to_do,
    )


def parse_extract_plan(content: str, prompt: str, signals: PageSignals) -> ExtractPlan:
    cleaned = _strip_json_fence(content)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise CommandPlannerError("The parent planner returned invalid JSON.") from exc
    if not isinstance(parsed, dict):
        raise CommandPlannerError("The parent planner returned invalid JSON.")
    return plan_from_mapping(parsed, prompt, signals)


def format_planner_signals(signals: PageSignals) -> str:
    index = signals.region_index.strip() or "(none)"
    return (
        f"url: {signals.url}\n"
        f"host: {signals.host}\n"
        f"asin: {signals.asin or '(none)'}\n"
        f"title: {signals.title or '(none)'}\n"
        f"accessWall: {str(signals.access_wall).lower()}\n"
        f"truncated: {str(signals.truncated).lower()}\n"
        f"availableTools: {', '.join(signals.available_tools)}\n"
        f"regionIndex:\n{index}"
    )


def plan_extract_job(prompt: str, signals: PageSignals) -> ExtractPlan:
    if not settings.reasoning_model_api_key:
        return heuristic_extract_plan(prompt, signals)

    template = load_prompt("web-extract-parent")
    filled_prompt = (
        template.replace("{prompt}", prompt)
        .replace("{signals}", format_planner_signals(signals))
        .replace("{tools}", ", ".join(signals.available_tools))
    )

    last_error: Exception | None = None
    for _ in range(2):
        try:
            response = deepseek_client.generate_completion(filled_prompt)
            content = (
                response.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            return parse_extract_plan(content, prompt, signals)
        except HTTPException:
            raise
        except Exception as exc:
            last_error = exc

    raise CommandPlannerError(
        "The parent planner could not produce an extraction plan.",
    ) from last_error
