import json

from fastapi import HTTPException

from config.settings import settings
from integrations.deepseek_client import deepseek_client
from prompts.load_prompt import load_prompt
from web_extract.command_planner import CommandPlannerError, _strip_json_fence

MAX_REFINED_PROMPT_CHARS = 1_600


def refine_user_prompt(prompt: str, url: str) -> str:
    cleaned_prompt = prompt.strip()
    if not cleaned_prompt or not settings.reasoning_model_api_key:
        return cleaned_prompt

    template = load_prompt("web-extract-input-refine")
    filled_prompt = (
        template.replace("{prompt}", cleaned_prompt)
        .replace("{url}", url)
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
            if not isinstance(content, str) or not content.strip():
                return cleaned_prompt
            parsed = json.loads(_strip_json_fence(content))
            if not isinstance(parsed, dict):
                return cleaned_prompt
            refined = parsed.get("refinedPrompt") or parsed.get("refined_prompt")
            if not isinstance(refined, str) or not refined.strip():
                return cleaned_prompt
            return refined.strip()[:MAX_REFINED_PROMPT_CHARS]
        except HTTPException:
            raise
        except (json.JSONDecodeError, CommandPlannerError) as exc:
            last_error = exc
        except Exception as exc:
            last_error = exc

    if last_error is not None:
        return cleaned_prompt
    return cleaned_prompt
