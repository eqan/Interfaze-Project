import json
import re

from fastapi import HTTPException

from config.settings import settings
from integrations.deepseek_client import deepseek_client
from prompts.load_prompt import load_prompt
from web_extract.dtos.web_extract import ExtractCommand

MAX_COMMANDS = 20


class CommandPlannerError(Exception):
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


def parse_extract_commands(content: str) -> list[ExtractCommand]:
    cleaned = _strip_json_fence(content)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise CommandPlannerError("The extraction planner returned invalid JSON.") from exc

    if not isinstance(parsed, dict):
        raise CommandPlannerError("The extraction planner returned an invalid command list.")

    raw_commands = parsed.get("commands")
    if not isinstance(raw_commands, list):
        raise CommandPlannerError("The extraction planner returned an invalid command list.")

    commands: list[ExtractCommand] = []
    for item in raw_commands[:MAX_COMMANDS]:
        try:
            commands.append(ExtractCommand.model_validate(item))
        except Exception:
            continue

    return commands


def plan_extract_commands(prompt: str, url: str, outline: str) -> list[ExtractCommand]:
    if not settings.reasoning_model_api_key:
        raise HTTPException(status_code=503, detail="Page extraction planner is not configured")

    template = load_prompt("web-extract-commands")
    filled_prompt = (
        template.replace("{prompt}", prompt)
        .replace("{url}", url)
        .replace("{outline}", outline)
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
            return parse_extract_commands(content)
        except HTTPException:
            raise
        except Exception as exc:
            last_error = exc

    raise CommandPlannerError(
        "The extraction planner could not produce usable commands.",
    ) from last_error
