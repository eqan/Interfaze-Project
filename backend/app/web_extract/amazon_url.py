import re
from urllib.parse import urlparse

AMAZON_HOST_SUFFIXES = (
    "amazon.com",
    "amazon.co.uk",
    "amazon.de",
    "amazon.fr",
    "amazon.it",
    "amazon.es",
    "amazon.ca",
    "amazon.co.jp",
    "amazon.in",
    "amazon.com.au",
    "amazon.com.mx",
    "amazon.com.br",
)
ASIN_PATTERNS = (
    re.compile(r"/dp/([A-Z0-9]{10})(?:[/?]|$)", re.IGNORECASE),
    re.compile(r"/gp/product/([A-Z0-9]{10})(?:[/?]|$)", re.IGNORECASE),
    re.compile(r"/product/([A-Z0-9]{10})(?:[/?]|$)", re.IGNORECASE),
)


def is_amazon_host(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == suffix or host.endswith(f".{suffix}") for suffix in AMAZON_HOST_SUFFIXES)


def extract_amazon_asin(url: str) -> str | None:
    if not is_amazon_host(url):
        return None

    for pattern in ASIN_PATTERNS:
        match = pattern.search(url)
        if match:
            return match.group(1).upper()
    return None
