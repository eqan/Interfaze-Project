import re
from html import escape
from urllib.parse import urlparse

from integrations.html_fetcher import HtmlFetchError, fetch_public_html
from web_extract.region_index import MAX_SLICE_CHARS, PageRegion

LLMS_REGION_KEY = "llms.txt"
LLMS_TXT_MAX_CHARS = 8_000
PROJECT_LINE_RE = re.compile(r"^-\s+(.+?)\s+\([^)\n]+\)\s*:", re.MULTILINE)


def same_origin_llms_txt_url(page_url: str) -> str:
    parsed = urlparse(page_url)
    return f"{parsed.scheme}://{parsed.netloc}/llms.txt"


def parse_llms_project_names(text: str) -> list[str]:
    names: list[str] = []
    for match in PROJECT_LINE_RE.finditer(text):
        name = match.group(1).strip()
        if name and name not in names:
            names.append(name)
    return names


def project_name_is_known(value: object, known_names: list[str]) -> bool:
    if isinstance(value, list):
        return any(project_name_is_known(item, known_names) for item in value)
    if not isinstance(value, str) or not value.strip():
        return False
    needle = value.strip().lower()
    for name in known_names:
        haystack = name.strip().lower()
        if needle == haystack or haystack in needle or needle in haystack:
            return True
    return False


def fetch_same_origin_llms_txt(page_url: str) -> str | None:
    try:
        document = fetch_public_html(same_origin_llms_txt_url(page_url), max_bytes=50_000)
    except HtmlFetchError:
        return None
    text = document.html.strip()
    if not text:
        return None
    return text[:LLMS_TXT_MAX_CHARS]


def attach_llms_txt_region(
    regions: list[PageRegion],
    html_by_key: dict[str, str],
    text: str,
) -> None:
    names = parse_llms_project_names(text)
    preview = ", ".join(names[:6]) or text[:120]
    regions.append(
        PageRegion(
            heading="llms.txt",
            key=LLMS_REGION_KEY,
            preview=preview[:120],
            tag="text",
        )
    )
    html_by_key[LLMS_REGION_KEY] = f"<pre id=\"llms-txt\">{escape(text[:MAX_SLICE_CHARS])}</pre>"
