import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from config.config import limiter
from config.settings import settings
from web_extract.dtos.web_extract import WebExtractRequest
from web_extract.webExtractService import web_extract_service

router = APIRouter(prefix="/web-extract")


@router.post("/extract-page", tags=["web-extract"])
@limiter.limit(settings.runtime.rate_limits.web_extract)
async def extract_page(payload: WebExtractRequest, request: Request):
    outcome = await asyncio.to_thread(web_extract_service.extract_page, payload)
    return JSONResponse(
        content=outcome.body.model_dump(mode="json", by_alias=True),
        status_code=outcome.status_code,
    )
