from ipaddress import ip_address

from pydantic import BaseModel, Field, HttpUrl, field_validator


class InterfazeIdExtractionRequest(BaseModel):
    image_url: HttpUrl = Field(
        ...,
        description="Public image URL for the ID document to parse with Interfaze.",
    )
    instruction: str = Field(
        default="Extract the details from this ID",
        min_length=10,
        max_length=500,
        description="Short instruction sent alongside the ID image.",
    )
    idempotency_key: str | None = Field(
        default=None,
        min_length=8,
        max_length=128,
        description="Stable key used to safely retry or deduplicate the same extraction request.",
    )

    @field_validator("image_url")
    @classmethod
    def validate_image_url(cls, value: HttpUrl) -> HttpUrl:
        if value.scheme != "https":
            raise ValueError("image_url must use https")

        host = value.host or ""
        if host == "localhost" or host.endswith(".local"):
            raise ValueError("image_url must point to a public host")

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
        ):
            raise ValueError("image_url must point to a public host")

        return value


class InterfazeIdExtractionResult(BaseModel):
    first_name: str = Field(..., description="First name on the ID")
    last_name: str = Field(..., description="Last name on the ID")
    dob: str = Field(..., description="Date of birth on the ID")
    driver_licence_number: str = Field(
        ...,
        description="Driver licence number on the ID",
    )


class InterfazeIdExtractionMeta(BaseModel):
    provider: str = "interfaze"
    cached: bool = False
    idempotency_key: str


class InterfazeIdExtractionExecution(BaseModel):
    result: InterfazeIdExtractionResult
    meta: InterfazeIdExtractionMeta


class InterfazeIdExtractionResponse(BaseModel):
    status: bool = True
    message: str = "Interfaze extraction completed"
    result: InterfazeIdExtractionResult
    meta: InterfazeIdExtractionMeta
