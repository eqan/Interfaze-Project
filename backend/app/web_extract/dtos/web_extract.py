from ipaddress import ip_address
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


def validate_public_https_url(value: HttpUrl) -> HttpUrl:
    if value.scheme != "https":
        raise ValueError("url must use https")

    host = value.host or ""
    if host == "localhost" or host.endswith(".local"):
        raise ValueError("url must point to a public host")

    try:
        parsed_ip = ip_address(host)
    except ValueError:
        return value

    if (
        parsed_ip.is_private
        or parsed_ip.is_loopback
        or parsed_ip.is_link_local
        or parsed_ip.is_multicast
        or parsed_ip.is_reserved
        or parsed_ip.is_unspecified
    ):
        raise ValueError("url must point to a public host")

    return value


class WebExtractRequest(CamelModel):
    url: HttpUrl = Field(..., description="Single public https page to extract from.")
    prompt: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="What to extract from the page.",
    )
    idempotency_key: str | None = Field(
        default=None,
        min_length=8,
        max_length=128,
        description="Stable key used to safely retry the same extract request.",
    )

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: HttpUrl) -> HttpUrl:
        return validate_public_https_url(value)

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("prompt must not be empty")
        return cleaned


class ExtractCommand(CamelModel):
    name: str = Field(..., min_length=1, max_length=64, pattern=r"^[A-Za-z][A-Za-z0-9_]*$")
    selector: str = Field(..., min_length=1, max_length=256)
    attr: str = Field(default="text", min_length=1, max_length=64)
    many: bool = False


class WebExtractResult(CamelModel):
    url: str
    data: dict[str, Any] = Field(default_factory=dict)
    commands: list[ExtractCommand] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0, le=1)


class WebExtractError(CamelModel):
    code: str
    message: str
    retriable: bool = False


class WebExtractMeta(CamelModel):
    request_id: str
    provider: str = "local-html+deepseek"
    cached: bool = False
    idempotency_key: str
    duration_ms: int = 0
    truncated: bool = False
    region_passes: int = 0
    site_type: str = ""
    tools_used: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    check_attempts: int = 0


class WebExtractResponse(CamelModel):
    status: bool
    message: str
    task: Literal["extract_page"] = "extract_page"
    result: WebExtractResult | None = None
    meta: WebExtractMeta
    errors: list[WebExtractError] = Field(default_factory=list)


class WebExtractOutcome(BaseModel):
    status_code: int
    body: WebExtractResponse
