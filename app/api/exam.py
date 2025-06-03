from fastapi import APIRouter, HTTPException, Query
from typing import List
from app.models.exam import ExamRequest, ExamDto
from app.services.exam_service import exam_service

router = APIRouter(prefix="/exams", tags=["exams"])


@router.post("", response_model=ExamDto)
async def generate_exam(request: ExamRequest):
    """
    Generate exam questions for a given topic using AI
    
    - **topic**: The subject or topic to generate exam questions for
    - **num_questions**: Number of questions to generate (default: 5)
    """
    try:
        if not request.topic.strip():
            raise HTTPException(status_code=400, detail="Topic cannot be empty")
        
        if request.num_questions < 1 or request.num_questions > 20:
            raise HTTPException(
                status_code=400, 
                detail="Number of questions must be between 1 and 20"
            )
        
        result = await exam_service.generate_exam(
            topic=request.topic,
            workspace_id=request.workspace_id,
            num_questions=request.num_questions
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in generate_exam endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate exam. Please try again."
        )

