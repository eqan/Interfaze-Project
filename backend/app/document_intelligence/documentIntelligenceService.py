import asyncio
from hashlib import sha256

from fastapi import HTTPException

from config.settings import settings
from document_intelligence.dtos.interfaze import (
    InterfazeIdExtractionExecution,
    InterfazeIdExtractionMeta,
    InterfazeIdExtractionRequest,
    InterfazeIdExtractionResult,
)
from integrations.interfaze_client import interfaze_client
from utils.cache import get_cache_service


class DocumentIntelligenceService:
    def _resolve_idempotency_key(self, payload: InterfazeIdExtractionRequest) -> str:
        if payload.idempotency_key:
            return payload.idempotency_key

        fingerprint = f"{payload.image_url}|{payload.instruction}"
        return sha256(fingerprint.encode("utf-8")).hexdigest()

    async def extract_id_details(
        self,
        payload: InterfazeIdExtractionRequest,
    ) -> InterfazeIdExtractionExecution:
        idempotency_key = self._resolve_idempotency_key(payload)
        cache = get_cache_service()
        cache_key = f"interfaze:extract-id:{idempotency_key}"
        cached_result = cache.get_json(cache_key)

        if cached_result is not None:
            return InterfazeIdExtractionExecution(
                result=InterfazeIdExtractionResult.model_validate(cached_result),
                meta=InterfazeIdExtractionMeta(
                    cached=True,
                    idempotency_key=idempotency_key,
                ),
            )

        max_attempts = max(settings.interfaze_retry_attempts, 1)
        for attempt in range(max_attempts):
            try:
                result = await asyncio.wait_for(
                    asyncio.to_thread(
                        interfaze_client.extract_id_details,
                        image_url=str(payload.image_url),
                        instruction=payload.instruction,
                    ),
                    timeout=settings.interfaze_timeout_seconds,
                )
                cache.set_json(cache_key, result.model_dump())
                return InterfazeIdExtractionExecution(
                    result=result,
                    meta=InterfazeIdExtractionMeta(
                        cached=False,
                        idempotency_key=idempotency_key,
                    ),
                )
            except HTTPException:
                raise
            except TimeoutError as exc:
                if attempt == max_attempts - 1:
                    raise HTTPException(
                        status_code=504,
                        detail="Interfaze extraction timed out",
                    ) from exc
            except Exception as exc:
                if attempt == max_attempts - 1:
                    raise HTTPException(
                        status_code=502,
                        detail="Interfaze extraction failed",
                    ) from exc


document_intelligence_service = DocumentIntelligenceService()
