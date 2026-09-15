import json

from integrations.deepseek_client import deepseek_client
from prompts.load_prompt import load_prompt


def extract_from_chunk(
    *,
    url: str,
    chunk: str,
    strategy_prompt: str,
    expected_output: dict[str, object],
    regex_hits: dict[str, object],
) -> dict[str, object]:
    prompt = load_prompt("web-extract-chunk")
    filled_prompt = (
        prompt.replace("{url}", url)
        .replace("{strategy_prompt}", strategy_prompt)
        .replace("{expected_output}", json.dumps(expected_output, ensure_ascii=True, indent=2))
        .replace("{regex_hits}", json.dumps(regex_hits, ensure_ascii=True, indent=2))
        .replace("{chunk}", chunk)
    )
    response = deepseek_client.generate_completion(filled_prompt)
    content = (
        response.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
        .strip()
    )
    if not content:
        return {}
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
