from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from app.generated_content.model import ExamDto
from app.generated_content.exam_service import exam_service

router = APIRouter(prefix="/exams", tags=["exams"])


class CreateExamRequest(BaseModel):
    topic: str = Field(..., alias="topic")
    workspace_id: str = Field(..., alias="workspaceId")
    num_questions: Optional[int] = Field(default=5)


@router.post("", response_model=ExamDto)
async def generate_exam(request: CreateExamRequest):
    """Generate exam questions for a given topic using AI"""

    try:
        return await exam_service.generate_exam(
            topic=request.topic,
            workspace_id=request.workspace_id,
            num_questions=request.num_questions or 5,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
