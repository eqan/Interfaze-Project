from fastapi import APIRouter, Depends, Request

from config.config import limiter
from config.settings import settings
from dependencies.auth import require_authenticated_payload
from document_intelligence.documentIntelligenceService import (
    document_intelligence_service,
)
from document_intelligence.dtos.interfaze import (
    InterfazeIdExtractionRequest,
    InterfazeIdExtractionResponse,
)

router = APIRouter(prefix="/interfaze")


@router.post(
    "/extract-id",
    response_model=InterfazeIdExtractionResponse,
    tags=["interfaze"],
)
@limiter.limit(settings.runtime.rate_limits.interfaze_extract)
async def extract_id_details(
    payload: InterfazeIdExtractionRequest,
    request: Request,
    _: dict = Depends(require_authenticated_payload),
):
    result = await document_intelligence_service.extract_id_details(payload)
    return InterfazeIdExtractionResponse(result=result)
