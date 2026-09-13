import asyncio

from document_intelligence.dtos.interfaze import (
    InterfazeIdExtractionRequest,
    InterfazeIdExtractionResult,
)
from integrations.interfaze_client import interfaze_client


class DocumentIntelligenceService:
    async def extract_id_details(
        self,
        payload: InterfazeIdExtractionRequest,
    ) -> InterfazeIdExtractionResult:
        return await asyncio.to_thread(
            interfaze_client.extract_id_details,
            image_url=str(payload.image_url),
            instruction=payload.instruction,
        )


document_intelligence_service = DocumentIntelligenceService()
