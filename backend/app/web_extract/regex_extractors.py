import re
from collections.abc import Sequence


def apply_regex_rules(
    text: str,
    rules: Sequence[dict[str, object]],
) -> dict[str, object]:
    data: dict[str, object] = {}
    for rule in rules:
        field_name = rule.get("field")
        pattern = rule.get("pattern")
        if not isinstance(field_name, str) or not isinstance(pattern, str):
            continue
        try:
            matches = re.findall(pattern, text, flags=re.IGNORECASE)
        except re.error:
            continue
        values: list[str] = []
        for match in matches:
            if isinstance(match, tuple):
                value = " ".join(str(item).strip() for item in match if str(item).strip())
            else:
                value = str(match).strip()
            if value and value not in values:
                values.append(value)
        if not values:
            continue
        data[field_name] = values if rule.get("many") is True else values[0]
    return data
