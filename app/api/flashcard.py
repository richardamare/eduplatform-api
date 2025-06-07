from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.generated_content.model import FlashcardDto
from app.generated_content.flashcard_service import flashcard_service

router = APIRouter(prefix="/flashcards", tags=["flashcards"])


class CreateFlashcardRequest(BaseModel):
    topic: str = Field(..., alias="topic")
    workspace_id: str = Field(..., alias="workspaceId")
    num_cards: int = Field(..., alias="numCards")


@router.post("", response_model=FlashcardDto)
async def generate_flashcards(request: CreateFlashcardRequest):
    """Generate flashcards for a given topic using AI"""

    try:
        return await flashcard_service.generate_flashcards(
            topic=request.topic,
            workspace_id=request.workspace_id,
            num_cards=request.num_cards,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
