from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.models.flashcard import FlashcardRequest, FlashcardDto, Flashcard
from app.services.flashcard_service import flashcard_service

router = APIRouter(prefix="/flashcards", tags=["flashcards"])


@router.post("", response_model=FlashcardDto)
async def generate_flashcards(request: FlashcardRequest):
    """
    Generate flashcards for a given topic using AI
    
    - **topic**: The subject or topic to generate flashcards for
    - **num_cards**: Number of flashcards to generate (default: 5)
    """
    try:
        if not request.topic.strip():
            raise HTTPException(status_code=400, detail="Topic cannot be empty")
        
        if request.num_cards < 1 or request.num_cards > 20:
            raise HTTPException(
                status_code=400, 
                detail="Number of cards must be between 1 and 20"
            )
        
        result = await flashcard_service.generate_flashcards(
            topic=request.topic,
            workspace_id=request.workspace_id,
            num_cards=request.num_cards
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in generate_flashcards endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate flashcards. Please try again."
        )

