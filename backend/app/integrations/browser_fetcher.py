import re

from integrations.html_fetcher import (
    DEFAULT_TIMEOUT_SECONDS,
    HtmlDocument,
    HtmlFetchError,
    validate_fetch_url,
)

CONTINUE_SHOPPING_NAMES = (
    "Continue shopping",
    "Continuar comprando",
    "Weiter einkaufen",
)


def fetch_html_with_browser(
    url: str,
    *,
    timeout_seconds: int = max(DEFAULT_TIMEOUT_SECONDS, 25),
) -> HtmlDocument:
    validate_fetch_url(url)

    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise HtmlFetchError(
            "FETCH_BLOCKED",
            "Browser fallback is not installed.",
            status_code=422,
            retriable=True,
        ) from exc

    timeout_ms = timeout_seconds * 1000
    html = ""
    truncated = False
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                for name in CONTINUE_SHOPPING_NAMES:
                    button = page.get_by_role("button", name=re.compile(re.escape(name), re.I))
                    if button.count() == 0:
                        continue
                    button.first.click(timeout=5000)
                    page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
                    break
                try:
                    page.wait_for_load_state("networkidle", timeout=8000)
                except PlaywrightTimeoutError:
                    pass
                html = page.content()
                truncated = len(html) > 1_000_000
                html = html[:1_000_000]
            finally:
                browser.close()
    except PlaywrightTimeoutError as exc:
        raise HtmlFetchError(
            "FETCH_TIMEOUT",
            "The page took too long to load in the browser.",
            status_code=504,
            retriable=True,
        ) from exc
    except HtmlFetchError:
        raise
    except Exception as exc:
        raise HtmlFetchError(
            "FETCH_FAILED",
            "The browser could not open the page.",
            status_code=502,
            retriable=True,
        ) from exc

    return HtmlDocument(
        final_url=url,
        html=html,
        status_code=200,
        truncated=truncated,
        url=url,
    )
