import uuid
from pydantic import BaseModel
from typing import Dict, List, Literal


class FlashcardItemDto(BaseModel):
    question: str
    answer: str


class FlashcardDto(BaseModel):
    items: List[FlashcardItemDto]
    total_count: int
    topic: str
    workspace_id: uuid.UUID


class TestQuestionDto(BaseModel):
    question: str
    answers: Dict[Literal["A", "B", "C", "D"], str]
    correct_answer: str


class ExamDto(BaseModel):
    items: List[TestQuestionDto]
    total_count: int
    topic: str
    workspace_id: uuid.UUID
