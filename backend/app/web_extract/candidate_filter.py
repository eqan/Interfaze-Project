import re

from bs4 import BeautifulSoup

from web_extract.html_sanitizer import _is_chrome

CONTENT_HEADINGS_KEY = "contentHeadings"
MAX_HEADINGS = 24
MAX_HEADING_CHARS = 180

CHROME_LABELS = {
    "about",
    "about me",
    "about us",
    "blog",
    "careers",
    "connect",
    "contact",
    "docs",
    "documentation",
    "education",
    "experience",
    "experiences",
    "expertise",
    "faq",
    "features",
    "home",
    "honors",
    "lets connect",
    "let's connect",
    "log in",
    "login",
    "menu",
    "next chapter",
    "pricing",
    "privacy",
    "project",
    "projects",
    "service",
    "services",
    "sign in",
    "sign up",
    "terms",
}
NAME_PREFIX_RE = re.compile(
    r"^(?:hi(?:\s+there)?|hello)?[,!\s]*(?:i(?:['’]?m| am)|this is)\s+",
    re.IGNORECASE,
)
ARTICLE_HEADING_SELECTORS = (
    "article h1",
    "article h2",
    "article h3",
    "main article h1",
    "main article h2",
    "main article h3",
)
SLOT_HINTS = (
    "address",
    "author",
    "company",
    "email",
    "job",
    "listing",
    "phone",
    "price",
    "product",
    "project",
    "review",
    "sku",
)
HEADING_SELECTORS = (
    "h1",
    "h2",
    "h3",
    "main h1",
    "main h2",
    "main h3",
)


def _normalize_label(value: str) -> str:
    return " ".join(value.lower().replace("’", "'").split())


def is_chrome_label(value: str) -> bool:
    return _normalize_label(value) in CHROME_LABELS


def strip_intro_prefix(value: str) -> str:
    cleaned = NAME_PREFIX_RE.sub("", value).strip(" -|:·")
    return cleaned or value.strip()


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        key = value.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(key)
    return unique


def _heading_text(element) -> str | None:
    if _is_chrome(element):
        return None
    text = " ".join(element.get_text(" ", strip=True).split())
    if len(text) < 2 or len(text) > MAX_HEADING_CHARS:
        return None
    return text


def _collect_selector_headings(soup: BeautifulSoup, selectors: tuple[str, ...]) -> list[str]:
    values: list[str] = []
    for selector in selectors:
        try:
            matches = soup.select(selector)
        except Exception:
            continue
        for element in matches:
            text = _heading_text(element)
            if text:
                values.append(text)
            if len(values) >= MAX_HEADINGS:
                return _unique(values)
    return _unique(values)


def harvest_article_headings(html: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    return _collect_selector_headings(soup, ARTICLE_HEADING_SELECTORS)


def harvest_content_headings(html: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    values = harvest_article_headings(html)
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    if title:
        values.append(title.split("|")[0].strip() or title)
    values.extend(_collect_selector_headings(soup, HEADING_SELECTORS))
    return _unique(values)[:MAX_HEADINGS]


def expand_and_filter_values(values: list[str]) -> list[str]:
    expanded: list[str] = []
    for value in values:
        stripped = strip_intro_prefix(value)
        for item in (stripped, value):
            if item and not is_chrome_label(item):
                expanded.append(item)
    return _unique(expanded)


def clean_candidate_map(candidates: dict[str, list[str]]) -> dict[str, list[str]]:
    return {
        name: expand_and_filter_values(values)
        for name, values in candidates.items()
        if expand_and_filter_values(values)
    }


def merge_heading_candidates(
    commands,
    css_candidates: dict[str, list[str]],
    headings: list[str],
    article_headings: list[str],
) -> dict[str, list[str]]:
    merged: dict[str, list[str]] = {}
    for command in commands:
        values = css_candidates.get(command.name, [])
        merged[command.name] = _unique([*values, *article_headings])
    useful_headings = expand_and_filter_values(headings)
    if useful_headings:
        merged[CONTENT_HEADINGS_KEY] = useful_headings
    return merged


def missing_command_fields(
    commands,
    css_candidates: dict[str, list[str]],
) -> list[str]:
    cleaned = clean_candidate_map(css_candidates)
    return [command.name for command in commands if not cleaned.get(command.name)]


def has_unmatched_selectors(html: str, commands) -> bool:
    soup = BeautifulSoup(html, "lxml")
    for command in commands:
        try:
            matches = soup.select(command.selector)
        except Exception:
            return True
        if not matches:
            return True
    return False


def prompt_has_unplanned_slots(prompt: str, commands) -> bool:
    planned = " ".join(f"{command.name} {command.selector}" for command in commands).lower()
    text = prompt.lower()
    return any(hint in text and hint not in planned for hint in SLOT_HINTS)


def is_sparse_page(commands, css_candidates: dict[str, list[str]], html: str) -> bool:
    missing = missing_command_fields(commands, css_candidates)
    if not missing:
        return False
    return not harvest_article_headings(html)


def needs_browser_render(
    prompt: str,
    commands,
    css_candidates: dict[str, list[str]],
    html: str,
) -> bool:
    if has_unmatched_selectors(html, commands):
        return True
    if prompt_has_unplanned_slots(prompt, commands):
        return True
    return is_sparse_page(commands, css_candidates, html)


def data_from_candidates(commands, candidates: dict[str, list[str]]) -> dict:
    data: dict = {}
    for command in commands:
        values = candidates.get(command.name, [])
        if not values:
            continue
        data[command.name] = values if command.many else values[0]
    return data
