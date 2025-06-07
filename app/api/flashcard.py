from fastapi import APIRouter, HTTPException
from app.models.flashcard import FlashcardDto
from app.services.flashcard_service import flashcard_service
from pydantic import BaseModel, Field

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
