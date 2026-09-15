from bs4 import BeautifulSoup, Comment

REMOVED_TAGS = {
    "script",
    "style",
    "noscript",
    "iframe",
    "svg",
    "canvas",
    "template",
    "link",
    "meta",
}
ACCESS_WALL_MARKERS = (
    "continue shopping",
    "robot check",
    "enter the characters you see",
    "access denied",
    "pardon our interruption",
    "sorry, we just need to make sure you're not a robot",
)
CHROME_TAGS = {"nav", "header", "footer", "aside"}
CHROME_ROLES = {"navigation", "banner", "contentinfo", "menu"}
OUTLINE_TAGS = ("h1", "h2", "h3", "h4", "p", "span", "a", "li", "td", "th", "button", "article")
MAX_OUTLINE_CHARS = 6_000
MAX_TEXT_SNIPPET = 160
MAX_CONTAINER_TEXT = 280


def looks_like_access_wall(html: str) -> bool:
    soup = BeautifulSoup(html, "lxml")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    visible = soup.get_text(" ", strip=True)
    haystack = f"{title} {visible}".lower()
    return any(marker in haystack for marker in ACCESS_WALL_MARKERS)


def page_title(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    if soup.title:
        title = soup.title.get_text(" ", strip=True)
        if title:
            return title[:180]
    heading = soup.find(["h1", "h2"])
    if heading:
        text = " ".join(heading.get_text(" ", strip=True).split())
        if text:
            return text[:180]
    return ""


def sanitize_html(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all(REMOVED_TAGS):
        tag.decompose()
    for comment in soup.find_all(string=lambda value: isinstance(value, Comment)):
        comment.extract()
    return str(soup)


def _is_chrome(element) -> bool:
    if element.name in CHROME_TAGS:
        return True
    role = element.get("role")
    if isinstance(role, str) and role.strip().lower() in CHROME_ROLES:
        return True
    return element.find_parent(list(CHROME_TAGS)) is not None


def build_dom_outline(html: str, max_chars: int = MAX_OUTLINE_CHARS) -> str:
    soup = BeautifulSoup(html, "lxml")
    lines: list[str] = []
    used = 0
    seen: set[str] = set()

    for element in soup.find_all(OUTLINE_TAGS):
        if _is_chrome(element):
            continue

        text = " ".join(element.get_text(" ", strip=True).split())
        if len(text) < 2 or len(text) > MAX_CONTAINER_TEXT:
            continue

        fingerprint = text.lower()
        if fingerprint in seen:
            continue
        seen.add(fingerprint)

        ident = element.name
        element_id = element.get("id")
        if isinstance(element_id, str) and element_id.strip():
            ident += f"#{element_id.strip()}"

        classes = element.get("class") or []
        if classes:
            ident += "." + ".".join(str(item) for item in classes[:2] if item)

        line = f"{ident} | {text[:MAX_TEXT_SNIPPET]}"
        if used + len(line) + 1 > max_chars:
            break
        lines.append(line)
        used += len(line) + 1

    return "\n".join(lines)
