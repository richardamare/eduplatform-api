from pydantic import BaseModel, Field
from typing import Dict, List, Literal, Optional


class TestQuestionDto(BaseModel):
    question: str
    answers: Dict[Literal["A", "B", "C", "D"], str]
    correct_answer: str


class ExamDto(BaseModel):
    test_questions: List[TestQuestionDto]
    total_count: int
    topic: str
    workspace_id: str
