from bs4 import BeautifulSoup

BLOCK_TAGS = (
    "title",
    "h1",
    "h2",
    "h3",
    "h4",
    "p",
    "li",
    "td",
    "th",
    "span",
    "a",
)
MAX_LINE_CHARS = 300
CHUNK_CHARS = 2_400
CHUNK_OVERLAP = 240


def _line_text(value: str) -> str:
    return " ".join(value.split())


def sanitize_to_plain_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    lines: list[str] = []
    seen: set[str] = set()

    if soup.title:
        title = _line_text(soup.title.get_text(" ", strip=True))
        if title:
            seen.add(title.lower())
            lines.append(f"title | {title[:MAX_LINE_CHARS]}")

    for element in soup.find_all(BLOCK_TAGS):
        text = _line_text(element.get_text(" ", strip=True))
        if not text:
            continue
        line = f"{element.name} | {text[:MAX_LINE_CHARS]}"
        href = element.get("href") if element.name == "a" else None
        if isinstance(href, str) and href.strip():
            line = f"{line} | {href.strip()}"
        fingerprint = line.lower()
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        lines.append(line)

    return "\n".join(lines)


def chunk_plain_text(text: str, chunk_chars: int = CHUNK_CHARS) -> list[str]:
    cleaned = text.strip()
    if not cleaned:
        return []
    if len(cleaned) <= chunk_chars:
        return [cleaned]

    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(len(cleaned), start + chunk_chars)
        chunks.append(cleaned[start:end])
        if end >= len(cleaned):
            break
        start = max(0, end - CHUNK_OVERLAP)
    return chunks
