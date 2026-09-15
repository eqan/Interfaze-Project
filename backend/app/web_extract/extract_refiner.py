import json
import re
from typing import Any

from fastapi import HTTPException

from config.settings import settings
from integrations.deepseek_client import deepseek_client
from prompts.load_prompt import load_prompt

MAX_CANDIDATE_CHARS = 3_500
MAX_VALUES_PER_FIELD = 12
MAX_VALUE_CHARS = 180


class ExtractRefineError(Exception):
    def __init__(self, message: str, retriable: bool = True):
        super().__init__(message)
        self.message = message
        self.retriable = retriable


def _strip_json_fence(content: str) -> str:
    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```[a-zA-Z]*\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()


def compact_candidates(candidates: dict[str, list[str]], max_chars: int = MAX_CANDIDATE_CHARS) -> str:
    payload: dict[str, list[str]] = {}
    used = 2
    for name, values in candidates.items():
        clipped: list[str] = []
        for value in values[:MAX_VALUES_PER_FIELD]:
            text = value[:MAX_VALUE_CHARS]
            extra = len(json.dumps(text, ensure_ascii=False)) + 4
            if used + extra > max_chars:
                break
            clipped.append(text)
            used += extra
        if clipped:
            payload[name] = clipped
        if used >= max_chars:
            break
    return json.dumps(payload, ensure_ascii=False)


def flatten_candidates(candidates: dict[str, list[str]]) -> list[str]:
    values: list[str] = []
    for items in candidates.values():
        values.extend(items)
    return values


def _normalize_grounding(value: str) -> str:
    return " ".join(value.lower().split())


def is_grounded(value: Any, corpus: list[str]) -> bool:
    if value in (None, "", [], {}):
        return False
    if isinstance(value, dict):
        nested = [item for item in value.values() if item not in (None, "", [], {})]
        return bool(nested) and all(is_grounded(item, corpus) for item in nested)
    if isinstance(value, list):
        return bool(value) and all(is_grounded(item, corpus) for item in value)
    if isinstance(value, (int, float, bool)):
        needle = _normalize_grounding(str(value))
        return any(needle in _normalize_grounding(item) for item in corpus)
    if not isinstance(value, str):
        return False
    needle = _normalize_grounding(value)
    if len(needle) < 2:
        return False
    return any(needle in _normalize_grounding(item) for item in corpus)


def parse_refined_data(content: str, candidates: dict[str, list[str]]) -> dict[str, Any]:
    cleaned = _strip_json_fence(content)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ExtractRefineError("The extraction refiner returned invalid JSON.") from exc

    if not isinstance(parsed, dict):
        raise ExtractRefineError("The extraction refiner returned invalid JSON.")

    raw_data = parsed.get("data", parsed)
    if not isinstance(raw_data, dict):
        raise ExtractRefineError("The extraction refiner returned invalid JSON.")

    corpus = flatten_candidates(candidates)
    data: dict[str, Any] = {}
    for key, value in raw_data.items():
        if not isinstance(key, str) or not key.strip():
            continue
        if is_grounded(value, corpus):
            data[key] = value
    return data


def refine_extract_data(prompt: str, url: str, candidates: dict[str, list[str]]) -> dict[str, Any]:
    if not candidates:
        return {}
    if not settings.reasoning_model_api_key:
        raise HTTPException(status_code=503, detail="Page extraction planner is not configured")

    template = load_prompt("web-extract-refine")
    filled_prompt = (
        template.replace("{prompt}", prompt)
        .replace("{url}", url)
        .replace("{candidates}", compact_candidates(candidates))
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
            return parse_refined_data(content, candidates)
        except HTTPException:
            raise
        except ExtractRefineError as exc:
            last_error = exc
        except Exception as exc:
            last_error = exc

    raise ExtractRefineError(
        "The extraction refiner could not produce grounded JSON.",
    ) from last_error
