from dataclasses import dataclass
from ipaddress import ip_address
from socket import getaddrinfo
from urllib.parse import urljoin, urlparse

import httpx

MAX_REDIRECTS = 5
DEFAULT_TIMEOUT_SECONDS = 15
DEFAULT_MAX_HTML_BYTES = 1_000_000
FETCH_HEADERS = {
    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
}


class HtmlFetchError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 502,
        retriable: bool = True,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.retriable = retriable


@dataclass(frozen=True)
class HtmlDocument:
    final_url: str
    html: str
    status_code: int
    url: str
    truncated: bool = False


def _reject_private_host(host: str) -> None:
    normalized = host.strip().lower().strip("[]")
    if not normalized or normalized == "localhost" or normalized.endswith(".local"):
        raise HtmlFetchError(
            "INVALID_REQUEST",
            "url must point to a public host",
            status_code=422,
            retriable=False,
        )

    try:
        parsed_ip = ip_address(normalized)
    except ValueError:
        try:
            addr_infos = getaddrinfo(normalized, 443)
        except OSError as exc:
            raise HtmlFetchError(
                "FETCH_FAILED",
                "The page host could not be resolved.",
                status_code=502,
                retriable=True,
            ) from exc

        for addr_info in addr_infos:
            _reject_private_host(addr_info[4][0])
        return

    if (
        parsed_ip.is_private
        or parsed_ip.is_loopback
        or parsed_ip.is_link_local
        or parsed_ip.is_multicast
        or parsed_ip.is_reserved
        or parsed_ip.is_unspecified
    ):
        raise HtmlFetchError(
            "INVALID_REQUEST",
            "url must point to a public host",
            status_code=422,
            retriable=False,
        )


def validate_fetch_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise HtmlFetchError(
            "INVALID_REQUEST",
            "url must use https",
            status_code=422,
            retriable=False,
        )

    _reject_private_host(parsed.hostname or "")
    return url


def read_bounded_bytes(chunks, max_bytes: int) -> tuple[bytes, bool]:
    parts: list[bytes] = []
    size = 0
    truncated = False
    for chunk in chunks:
        if not chunk:
            continue
        remaining = max_bytes - size
        if remaining <= 0:
            truncated = True
            break
        if len(chunk) > remaining:
            parts.append(chunk[:remaining])
            truncated = True
            break
        parts.append(chunk)
        size += len(chunk)
    return b"".join(parts), truncated


def fetch_public_html(
    url: str,
    *,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    max_bytes: int = DEFAULT_MAX_HTML_BYTES,
) -> HtmlDocument:
    current_url = validate_fetch_url(url)

    with httpx.Client(
        timeout=timeout_seconds,
        follow_redirects=False,
        headers=FETCH_HEADERS,
    ) as client:
        for _ in range(MAX_REDIRECTS):
            try:
                with client.stream("GET", current_url) as response:
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location:
                            raise HtmlFetchError(
                                "FETCH_FAILED",
                                "The page redirected without a destination.",
                                status_code=502,
                                retriable=True,
                            )
                        current_url = validate_fetch_url(urljoin(current_url, location))
                        continue

                    if response.status_code >= 400:
                        raise HtmlFetchError(
                            "FETCH_FAILED",
                            f"The page returned HTTP {response.status_code}.",
                            status_code=502,
                            retriable=response.status_code >= 500,
                        )

                    content_type = (response.headers.get("content-type") or "").lower()
                    if content_type and not any(
                        token in content_type for token in ("html", "text/plain", "xml")
                    ):
                        raise HtmlFetchError(
                            "FETCH_FAILED",
                            "The URL did not return HTML.",
                            status_code=422,
                            retriable=False,
                        )

                    raw, truncated = read_bounded_bytes(response.iter_bytes(), max_bytes)
                    html = raw.decode(response.encoding or "utf-8", errors="replace")
                    return HtmlDocument(
                        final_url=str(response.url) or current_url,
                        html=html,
                        status_code=response.status_code,
                        truncated=truncated,
                        url=url,
                    )
            except HtmlFetchError:
                raise
            except httpx.TimeoutException as exc:
                raise HtmlFetchError(
                    "FETCH_TIMEOUT",
                    "The page took too long to load.",
                    status_code=504,
                    retriable=True,
                ) from exc
            except httpx.HTTPError as exc:
                raise HtmlFetchError(
                    "FETCH_FAILED",
                    "The page could not be downloaded.",
                    status_code=502,
                    retriable=True,
                ) from exc

    raise HtmlFetchError(
        "FETCH_FAILED",
        "The page redirected too many times.",
        status_code=502,
        retriable=True,
    )
