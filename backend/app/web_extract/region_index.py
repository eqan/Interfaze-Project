from dataclasses import dataclass

from bs4 import BeautifulSoup

from web_extract.completeness import prompt_search_terms
from web_extract.html_sanitizer import _is_chrome

MAX_REGIONS = 40
MAX_PREVIEW_CHARS = 120
MAX_SLICE_CHARS = 4_000
MAX_TOTAL_SLICE_CHARS = 12_000
MAX_WINDOWS = 4
WINDOW_CHARS = 2_400
REGION_TAGS = ("main", "section", "article")
HEADING_TAGS = ("h1", "h2", "h3")


@dataclass(frozen=True)
class PageRegion:
    heading: str
    key: str
    preview: str
    tag: str


def _text(element) -> str:
    return " ".join(element.get_text(" ", strip=True).split())


def _heading_for(element) -> str:
    if element.name in HEADING_TAGS:
        return _text(element)[:MAX_PREVIEW_CHARS]
    heading = element.find(HEADING_TAGS)
    if heading:
        return _text(heading)[:MAX_PREVIEW_CHARS]
    title = element.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()[:MAX_PREVIEW_CHARS]
    return _text(element)[:80]


def _region_key(element, index: int) -> str:
    element_id = element.get("id")
    if isinstance(element_id, str) and element_id.strip():
        return element_id.strip()
    classes = [item for item in (element.get("class") or []) if item]
    if classes:
        return f"{element.name}-{classes[0]}"
    return f"{element.name}-{index}"


def _append_region(
    element,
    index: int,
    seen: set[str],
    regions: list[PageRegion],
    html_by_key: dict[str, str],
) -> None:
    key = _region_key(element, index)
    if key in seen:
        return
    heading = _heading_for(element)
    preview = _text(element)[:MAX_PREVIEW_CHARS]
    if len(preview) < 2 and not element.get("id"):
        return
    seen.add(key)
    regions.append(PageRegion(heading=heading, key=key, preview=preview, tag=element.name))
    html_by_key[key] = str(element)[:MAX_SLICE_CHARS]


def build_region_index(html: str) -> tuple[list[PageRegion], dict[str, str]]:
    soup = BeautifulSoup(html, "lxml")
    regions: list[PageRegion] = []
    html_by_key: dict[str, str] = {}
    seen: set[str] = set()

    candidates = []
    for element in soup.find_all((*REGION_TAGS, *HEADING_TAGS)):
        if _is_chrome(element):
            continue
        if element.name in HEADING_TAGS and element.find_parent(list(REGION_TAGS)):
            continue
        candidates.append(element)

    for index, element in enumerate(candidates):
        _append_region(element, index, seen, regions, html_by_key)
        if len(regions) >= MAX_REGIONS:
            return regions, html_by_key

    extras = []
    for element in soup.find_all(id=True):
        if _is_chrome(element) or element.name in {*REGION_TAGS, *HEADING_TAGS}:
            continue
        preview = _text(element)
        if len(preview) < 24:
            continue
        extras.append((len(preview), element))
    extras.sort(key=lambda item: item[0], reverse=True)

    for offset, (_length, element) in enumerate(extras):
        _append_region(element, len(candidates) + offset, seen, regions, html_by_key)
        if len(regions) >= MAX_REGIONS:
            break

    return regions, html_by_key


def compact_region_index(regions: list[PageRegion]) -> str:
    lines = [
        f"{region.key} | {region.tag} | {region.heading} | {region.preview}"
        for region in regions
    ]
    return "\n".join(lines)


def slice_selected_regions(html_by_key: dict[str, str], keys: list[str]) -> list[tuple[str, str]]:
    slices: list[tuple[str, str]] = []
    used = 0
    for key in keys:
        html = html_by_key.get(key)
        if not html:
            continue
        remaining = MAX_TOTAL_SLICE_CHARS - used
        if remaining <= 0:
            break
        clipped = html[: min(MAX_SLICE_CHARS, remaining)]
        slices.append((key, clipped))
        used += len(clipped)
    return slices


def format_slices(slices: list[tuple[str, str]]) -> str:
    parts = [f"<!-- region:{key} -->\n{html}" for key, html in slices]
    return "\n\n".join(parts)


def slice_prompt_windows(html: str, prompt: str) -> list[tuple[str, str]]:
    terms = prompt_search_terms(prompt)
    if not html.strip() or not terms:
        return []

    haystack = html.lower()
    spans: list[tuple[int, int, str]] = []
    for term in terms:
        start = 0
        while len(spans) < MAX_WINDOWS * 3:
            index = haystack.find(term, start)
            if index < 0:
                break
            left = max(0, index - WINDOW_CHARS // 2)
            right = min(len(html), index + len(term) + WINDOW_CHARS // 2)
            spans.append((left, right, term))
            start = index + max(len(term), 1)

    spans.sort()
    merged: list[tuple[int, int, str]] = []
    for left, right, term in spans:
        if merged and left <= merged[-1][1]:
            prev_left, prev_right, prev_term = merged[-1]
            merged[-1] = (prev_left, max(prev_right, right), prev_term)
            continue
        merged.append((left, right, term))

    slices: list[tuple[str, str]] = []
    used = 0
    for index, (left, right, term) in enumerate(merged[:MAX_WINDOWS]):
        remaining = MAX_TOTAL_SLICE_CHARS - used
        if remaining <= 0:
            break
        clipped = html[left:right][: min(MAX_SLICE_CHARS, remaining)]
        if not clipped.strip():
            continue
        slices.append((f"window-{term}-{index}", clipped))
        used += len(clipped)
    return slices
