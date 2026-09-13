from fastapi import HTTPException

from config.config import get_interfaze_client
from config.settings import settings
from document_intelligence.dtos.interfaze import InterfazeIdExtractionResult


class InterfazeClient:
    def extract_id_details(
        self,
        *,
        image_url: str,
        instruction: str,
    ) -> InterfazeIdExtractionResult:
        try:
            client = get_interfaze_client()
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        if client is None:
            raise HTTPException(status_code=503, detail="Interfaze is not configured")

        response = client.chat.completions.parse(
            model=settings.interfaze_model_name,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": instruction},
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url},
                        },
                    ],
                }
            ],
            response_format=InterfazeIdExtractionResult,
        )

        parsed = response.choices[0].message.parsed
        if parsed is None:
            raise HTTPException(
                status_code=502,
                detail="Interfaze did not return a parsed ID payload",
            )

        if isinstance(parsed, InterfazeIdExtractionResult):
            return parsed

        return InterfazeIdExtractionResult.model_validate(parsed)


interfaze_client = InterfazeClient()
