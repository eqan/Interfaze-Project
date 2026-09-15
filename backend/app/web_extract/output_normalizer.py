import json

from integrations.deepseek_client import deepseek_client
from prompts.load_prompt import load_prompt


def normalize_extract_output(
    *,
    url: str,
    user_prompt: str,
    expected_output: dict[str, object],
    extracted_data: dict[str, object],
) -> dict[str, object]:
    prompt = load_prompt("web-extract-normalize")
    filled_prompt = (
        prompt.replace("{url}", url)
        .replace("{user_prompt}", user_prompt)
        .replace("{expected_output}", json.dumps(expected_output, ensure_ascii=True, indent=2))
        .replace("{extracted_data}", json.dumps(extracted_data, ensure_ascii=True, indent=2))
    )
    response = deepseek_client.generate_completion(filled_prompt)
    content = (
        response.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
        .strip()
    )
    if not content:
        return extracted_data
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return extracted_data
    return parsed if isinstance(parsed, dict) else extracted_data
