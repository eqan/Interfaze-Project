from typing import Any

from fastapi import HTTPException

from config.settings import settings
from integrations.deepseek_client import deepseek_client
from prompts.load_prompt import load_prompt
from web_extract.extract_refiner import ExtractRefineError, parse_refined_data


def extract_from_slices(prompt: str, url: str, slices: str) -> dict[str, Any]:
    if not slices.strip():
        return {}
    if not settings.reasoning_model_api_key:
        raise HTTPException(status_code=503, detail="Page extraction planner is not configured")

    template = load_prompt("web-extract-from-slices")
    filled_prompt = (
        template.replace("{prompt}", prompt)
        .replace("{url}", url)
        .replace("{slices}", slices)
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
            return parse_refined_data(content, {"slice": [slices]})
        except HTTPException:
            raise
        except ExtractRefineError as exc:
            last_error = exc
        except Exception as exc:
            last_error = exc

    raise ExtractRefineError(
        "The slice extractor could not produce grounded JSON.",
    ) from last_error
