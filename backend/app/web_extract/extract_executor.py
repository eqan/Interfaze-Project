from typing import Any

from bs4 import BeautifulSoup

from web_extract.dtos.web_extract import ExtractCommand

MAX_MANY_VALUES = 50
MAX_CANDIDATES_PER_FIELD = 12


def _read_value(element, attr: str) -> str | None:
    if attr == "text":
        text = " ".join(element.get_text(" ", strip=True).split())
        return text or None

    raw_value = element.get(attr)
    if raw_value is None:
        return None
    if isinstance(raw_value, list):
        joined = " ".join(str(item) for item in raw_value if item).strip()
        return joined or None
    value = str(raw_value).strip()
    return value or None


def collect_extract_candidates(html: str, commands: list[ExtractCommand]) -> dict[str, list[str]]:
    soup = BeautifulSoup(html, "lxml")
    candidates: dict[str, list[str]] = {}

    for command in commands:
        try:
            matches = soup.select(command.selector)
        except Exception:
            continue

        values: list[str] = []
        limit = MAX_MANY_VALUES if command.many else MAX_CANDIDATES_PER_FIELD
        for element in matches:
            value = _read_value(element, command.attr)
            if value and value not in values:
                values.append(value)
            if len(values) >= limit:
                break

        if values:
            candidates[command.name] = values

    return candidates


def execute_extract_commands(html: str, commands: list[ExtractCommand]) -> dict[str, Any]:
    candidates = collect_extract_candidates(html, commands)
    data: dict[str, Any] = {}
    command_by_name = {command.name: command for command in commands}

    for name, values in candidates.items():
        command = command_by_name.get(name)
        data[name] = values if command and command.many else values[0]

    return data
