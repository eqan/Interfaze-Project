# pyright: reportMissingImports=false

from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup


PROFILE_PLATFORM_HOSTS = {
    "fiverr.com": "fiverr",
    "upwork.com": "upwork",
    "linkedin.com": "linkedin",
    "github.com": "github",
    "contra.com": "contra",
}

SKIP_SCHEMES = ("javascript:", "mailto:", "tel:")
MAX_LINKS = 80
MAX_CONTEXT_CHARS = 200


def _normalized_text(value: str) -> str:
    return " ".join(value.split())


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def _same_origin(host: str, page_host: str) -> bool:
    return bool(host) and bool(page_host) and (host == page_host or host.endswith(f".{page_host}"))


def _platform_for_host(host: str) -> str:
    for domain, label in PROFILE_PLATFORM_HOSTS.items():
        if host == domain or host.endswith(f".{domain}"):
            return label
    return host


def collect_link_inventory(html: str, page_url: str) -> list[dict[str, object]]:
    soup = BeautifulSoup(html, "lxml")
    page_host = _host(page_url)
    links: list[dict[str, object]] = []
    seen: set[str] = set()

    for anchor in soup.select("a[href]"):
        href = str(anchor.get("href") or "").strip()
        if not href or href.startswith(SKIP_SCHEMES):
            continue
        absolute = urljoin(page_url, href)
        if absolute in seen:
            continue
        seen.add(absolute)
        host = _host(absolute)
        text = _normalized_text(anchor.get_text(" ", strip=True))
        context = _normalized_text(anchor.parent.get_text(" ", strip=True))[:MAX_CONTEXT_CHARS]
        links.append(
            {
                "url": absolute,
                "host": host,
                "platform": _platform_for_host(host),
                "anchorText": text,
                "context": context,
                "sameOrigin": _same_origin(host, page_host),
            }
        )
        if len(links) >= MAX_LINKS:
            break

    return links


def extract_profile_links(
    inventory: list[dict[str, object]],
    allowed_domains: list[str] | tuple[str, ...] | None = None,
    *,
    must_be_outbound: bool = True,
) -> dict[str, object]:
    allowed = [item.strip().lower() for item in (allowed_domains or []) if isinstance(item, str) and item.strip()]
    profiles: list[dict[str, str]] = []

    for item in inventory:
        url = item.get("url")
        host = str(item.get("host") or "").lower()
        if not isinstance(url, str) or not url:
            continue
        if must_be_outbound and item.get("sameOrigin") is True:
            continue
        if allowed and not any(host == domain or host.endswith(f".{domain}") for domain in allowed):
            continue
        profile = {
            "platform": str(item.get("platform") or host),
            "url": url,
        }
        anchor_text = str(item.get("anchorText") or "").strip()
        if anchor_text:
            profile["anchorText"] = anchor_text
        if profile not in profiles:
            profiles.append(profile)

    return {"profiles": profiles}
