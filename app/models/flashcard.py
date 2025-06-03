from pydantic import BaseModel, Field
from typing import List, Optional



class FlashcardRequest(BaseModel):
    model_config = {"populate_by_name": True}
    
    topic: str
    workspace_id: str = Field(..., alias="workspaceId")
    num_cards: Optional[int] = Field(default=5, alias="numCards")


class Flashcard(BaseModel):
    question: str
    answer: str


class FlashcardDto(BaseModel):
    model_config = {"populate_by_name": True}
    
    flashcards: List[Flashcard]
    total_count: int = Field(..., alias="totalCount")
    topic: str
    workspace_id: str = Field(..., alias="workspaceId")