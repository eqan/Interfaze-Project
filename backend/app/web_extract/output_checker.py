from dataclasses import dataclass
import json

from fastapi import HTTPException

from config.settings import settings
from integrations.deepseek_client import deepseek_client
from prompts.load_prompt import load_prompt
from web_extract.command_planner import CommandPlannerError, _strip_json_fence
from web_extract.completeness import extract_needs_another_pass

CONFIDENCE_THRESHOLD = 0.9
MAX_OUTPUT_ATTEMPTS = 3
MAX_OUTPUT_CHARS = 4_000


@dataclass(frozen=True)
class OutputCheck:
    confidence: float
    reason: str = ""
    missing: tuple[str, ...] = ()
    keep: tuple[str, ...] = ()


def clamp_confidence(value) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    if confidence < 0:
        return 0.0
    if confidence > 1:
        return 1.0
    return round(confidence, 4)


def parse_output_check(content: str) -> OutputCheck:
    cleaned = _strip_json_fence(content)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise CommandPlannerError("The output checker returned invalid JSON.") from exc
    if not isinstance(parsed, dict):
        raise CommandPlannerError("The output checker returned invalid JSON.")

    missing_raw = parsed.get("missing") or []
    missing: list[str] = []
    if isinstance(missing_raw, list):
        for item in missing_raw:
            if isinstance(item, str) and item.strip() and item not in missing:
                missing.append(item.strip())

    keep_raw = parsed.get("keep") or []
    keep: list[str] = []
    if isinstance(keep_raw, list):
        for item in keep_raw:
            if isinstance(item, str) and item.strip() and item not in keep:
                keep.append(item.strip())

    reason = parsed.get("reason") or ""
    if not isinstance(reason, str):
        reason = ""
    return OutputCheck(
        confidence=clamp_confidence(parsed.get("confidence", parsed.get("probability"))),
        reason=reason.strip()[:240],
        missing=tuple(missing[:12]),
        keep=tuple(keep[:12]),
    )


def _field_tokens(names: tuple[str, ...] | list[str]) -> list[str]:
    tokens: list[str] = []
    for item in names:
        token = item.strip().lower()
        if token and token not in tokens:
            tokens.append(token)
    return tokens


def _field_matches(name: str, tokens: list[str]) -> bool:
    key = name.lower()
    return any(token == key or token in key or key in token for token in tokens)


def kept_extract(data: dict, verdict: OutputCheck) -> dict:
    if not data:
        return {}
    missing = _field_tokens(verdict.missing)
    keep = _field_tokens(verdict.keep)
    kept: dict = {}
    for key, value in data.items():
        if missing and _field_matches(str(key), missing):
            continue
        if keep and not _field_matches(str(key), keep):
            continue
        kept[key] = value
    return kept


def heuristic_output_check(prompt: str, data: dict) -> OutputCheck:
    present = tuple(str(key) for key in data.keys())
    if not data:
        return OutputCheck(confidence=0.0, reason="The extract was empty.", missing=("data",))
    if extract_needs_another_pass(prompt, data):
        return OutputCheck(
            confidence=0.4,
            reason="The extract does not cover the requested fields.",
            keep=present,
        )
    return OutputCheck(confidence=0.95, reason="Requested fields are present.", keep=present)


def check_extract_output(
    prompt: str,
    url: str,
    data: dict,
    expected_output: dict | None = None,
    verification_rules: tuple[str, ...] | list[str] | None = None,
) -> OutputCheck:
    if not settings.reasoning_model_api_key:
        return heuristic_output_check(prompt, data)

    template = load_prompt("web-extract-check")
    payload = json.dumps(data, ensure_ascii=False)[:MAX_OUTPUT_CHARS]
    expected = json.dumps(expected_output or {}, ensure_ascii=False)[:MAX_OUTPUT_CHARS]
    rules = "\n".join(f"- {rule}" for rule in (verification_rules or ())) or "- none"
    filled_prompt = (
        template.replace("{prompt}", prompt)
        .replace("{url}", url)
        .replace("{expected_output}", expected)
        .replace("{verification_rules}", rules)
        .replace("{output}", payload)
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
            return parse_output_check(content)
        except HTTPException:
            raise
        except Exception as exc:
            last_error = exc

    raise CommandPlannerError(
        "The output checker could not score the extract.",
    ) from last_error
