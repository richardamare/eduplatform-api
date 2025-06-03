from pydantic import BaseModel, Field
from typing import List, Optional


class ExamRequest(BaseModel):
    model_config = {"populate_by_name": True}
    
    topic: str
    workspace_id: str = Field(..., alias="workspaceId")
    num_questions: Optional[int] = Field(default=5, alias="numQuestions")


class TestQuestion(BaseModel):
    question: str
    answer_a: str = Field(..., alias="answerA")
    answer_b: str = Field(..., alias="answerB")
    answer_c: str = Field(..., alias="answerC")
    answer_d: str = Field(..., alias="answerD")
    correct_answer: str = Field(..., alias="correct_answer")


class ExamDto(BaseModel):
    model_config = {"populate_by_name": True}
    
    test_questions: List[TestQuestion] = Field(..., alias="testQuestions")
    total_count: int = Field(..., alias="totalCount")
    topic: str
    workspace_id: str = Field(..., alias="workspaceId") 