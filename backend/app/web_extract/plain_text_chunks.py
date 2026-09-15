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


def _effective_overlap(chunk_chars: int) -> int:
    if chunk_chars <= 1:
        return 0
    return min(CHUNK_OVERLAP, max(1, chunk_chars // 10), chunk_chars - 1)


def _joined_length(blocks: list[str]) -> int:
    if not blocks:
        return 0
    return sum(len(block) for block in blocks) + max(len(blocks) - 1, 0)


def _tail_blocks_for_overlap(blocks: list[str], overlap_chars: int) -> list[str]:
    if not blocks or overlap_chars <= 0:
        return []
    kept: list[str] = []
    total = 0
    for block in reversed(blocks):
        block_size = len(block) + (1 if kept else 0)
        if kept and total + block_size > overlap_chars:
            break
        kept.append(block)
        total += block_size
    kept.reverse()
    return kept


def _split_large_block(block: str, chunk_chars: int) -> list[str]:
    overlap_chars = _effective_overlap(chunk_chars)
    pieces: list[str] = []
    start = 0
    while start < len(block):
        end = min(len(block), start + chunk_chars)
        pieces.append(block[start:end])
        if end >= len(block):
            break
        next_start = end - overlap_chars
        if next_start <= start:
            next_start = end
        start = next_start
    return pieces


def chunk_plain_text(text: str, chunk_chars: int = CHUNK_CHARS) -> list[str]:
    cleaned = text.strip()
    if not cleaned:
        return []
    if len(cleaned) <= chunk_chars:
        return [cleaned]

    overlap_chars = _effective_overlap(chunk_chars)
    blocks = [line.strip() for line in cleaned.splitlines() if line.strip()]
    if not blocks:
        return _split_large_block(cleaned, chunk_chars)

    chunks: list[str] = []
    current: list[str] = []

    for block in blocks:
        if len(block) > chunk_chars:
            if current:
                chunks.append("\n".join(current))
                current = []
            chunks.extend(_split_large_block(block, chunk_chars))
            continue

        candidate = [*current, block]
        if _joined_length(candidate) <= chunk_chars:
            current = candidate
            continue

        if current:
            chunks.append("\n".join(current))
            overlap_blocks = _tail_blocks_for_overlap(current, overlap_chars)
            if _joined_length([*overlap_blocks, block]) <= chunk_chars:
                current = [*overlap_blocks, block]
            else:
                current = [block]
            continue

        current = [block]

    if current:
        chunks.append("\n".join(current))

    return chunks
