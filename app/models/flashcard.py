from pydantic import BaseModel
from typing import List


class FlashcardItemDto(BaseModel):
    question: str
    answer: str


class FlashcardDto(BaseModel):
    items: List[FlashcardItemDto]
    total_count: int
    topic: str
    workspace_id: str
