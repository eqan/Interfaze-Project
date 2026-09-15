from dataclasses import dataclass
from threading import Lock
from time import monotonic

import httpx

from config.settings import settings

TOKEN_SCOPE = "creatorsapi::default"
GET_ITEMS_URL = "https://creatorsapi.amazon/catalog/v1/getItems"


class AmazonCreatorsError(Exception):
    def __init__(self, message: str, retriable: bool = True):
        super().__init__(message)
        self.message = message
        self.retriable = retriable


@dataclass(frozen=True)
class AmazonCatalogItem:
    asin: str
    name: str
    price: str | None = None


_token_lock = Lock()
_cached_token: str | None = None
_token_expires_at = 0.0


def is_amazon_catalog_configured() -> bool:
    return bool(
        settings.amazon_creators_client_id.strip()
        and settings.amazon_creators_client_secret.strip()
        and settings.amazon_partner_tag.strip()
    )


def _read_nested(payload: dict, *keys: str):
    current = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        if key in current:
            current = current[key]
            continue
        camel = key[:1].lower() + key[1:] if key else key
        pascal = key[:1].upper() + key[1:] if key else key
        if camel in current:
            current = current[camel]
            continue
        if pascal in current:
            current = current[pascal]
            continue
        return None
    return current


def _parse_item(payload: dict, asin: str) -> AmazonCatalogItem | None:
    items = _read_nested(payload, "items") or _read_nested(payload, "Items") or []
    if isinstance(payload.get("itemResults"), dict):
        items = payload["itemResults"].get("items") or payload["itemResults"].get("Items") or items
    if not isinstance(items, list):
        return None

    for item in items:
        if not isinstance(item, dict):
            continue
        item_asin = str(item.get("asin") or item.get("ASIN") or "").upper()
        title = _read_nested(item, "itemInfo", "title", "displayValue")
        if not title:
            title = _read_nested(item, "ItemInfo", "Title", "DisplayValue")
        listings = _read_nested(item, "offersV2", "listings") or _read_nested(item, "OffersV2", "Listings") or []
        price = None
        if isinstance(listings, list) and listings:
            price = _read_nested(listings[0], "price", "displayAmount")
            if not price:
                price = _read_nested(listings[0], "Price", "DisplayAmount")
        if title and (not item_asin or item_asin == asin):
            return AmazonCatalogItem(asin=asin, name=str(title).strip(), price=str(price).strip() if price else None)
    return None


def _request_access_token() -> str:
    global _cached_token, _token_expires_at
    now = monotonic()
    with _token_lock:
        if _cached_token and now < _token_expires_at:
            return _cached_token

        try:
            response = httpx.post(
                settings.amazon_token_url,
                json={
                    "client_id": settings.amazon_creators_client_id,
                    "client_secret": settings.amazon_creators_client_secret,
                    "grant_type": "client_credentials",
                    "scope": TOKEN_SCOPE,
                },
                timeout=20,
            )
        except httpx.HTTPError as exc:
            raise AmazonCreatorsError("Amazon catalog authentication failed.") from exc

        if not response.is_success:
            raise AmazonCreatorsError("Amazon catalog authentication failed.")

        payload = response.json()
        token = payload.get("access_token")
        expires_in = int(payload.get("expires_in") or 3600)
        if not token:
            raise AmazonCreatorsError("Amazon catalog authentication failed.")

        _cached_token = token
        _token_expires_at = now + max(expires_in - 60, 30)
        return token


def lookup_amazon_item(asin: str) -> AmazonCatalogItem | None:
    if not is_amazon_catalog_configured():
        return None

    token = _request_access_token()
    marketplace = settings.amazon_marketplace
    try:
        response = httpx.post(
            GET_ITEMS_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "x-marketplace": marketplace,
            },
            json={
                "itemIds": [asin],
                "itemIdType": "ASIN",
                "marketplace": marketplace,
                "partnerTag": settings.amazon_partner_tag,
                "partnerType": "Associates",
                "resources": [
                    "itemInfo.title",
                    "offersV2.listings.price",
                ],
            },
            timeout=20,
        )
    except httpx.HTTPError as exc:
        raise AmazonCreatorsError("Amazon catalog lookup failed.") from exc

    if not response.is_success:
        raise AmazonCreatorsError("Amazon catalog lookup failed.")

    return _parse_item(response.json(), asin)
