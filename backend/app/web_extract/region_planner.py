import json

from fastapi import HTTPException

from config.settings import settings
from integrations.deepseek_client import deepseek_client
from prompts.load_prompt import load_prompt
from web_extract.command_planner import CommandPlannerError, _strip_json_fence

MAX_SELECTED_REGIONS = 8


def parse_region_keys(content: str, allowed: set[str]) -> list[str]:
    cleaned = _strip_json_fence(content)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise CommandPlannerError("The region planner returned invalid JSON.") from exc

    if not isinstance(parsed, dict):
        raise CommandPlannerError("The region planner returned invalid JSON.")

    raw_keys = parsed.get("regions", parsed.get("keys", []))
    if not isinstance(raw_keys, list):
        raise CommandPlannerError("The region planner returned invalid JSON.")

    keys: list[str] = []
    for item in raw_keys:
        if not isinstance(item, str):
            continue
        key = item.strip()
        if key in allowed and key not in keys:
            keys.append(key)
        if len(keys) >= MAX_SELECTED_REGIONS:
            break
    return keys


def plan_relevant_regions(prompt: str, url: str, index: str, allowed: set[str]) -> list[str]:
    if not allowed:
        return []
    if not settings.reasoning_model_api_key:
        raise HTTPException(status_code=503, detail="Page extraction planner is not configured")

    template = load_prompt("web-extract-regions")
    filled_prompt = (
        template.replace("{prompt}", prompt)
        .replace("{url}", url)
        .replace("{index}", index)
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
            return parse_region_keys(content, allowed)
        except HTTPException:
            raise
        except Exception as exc:
            last_error = exc

    raise CommandPlannerError(
        "The region planner could not select page regions.",
    ) from last_error
