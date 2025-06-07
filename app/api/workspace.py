from fastapi import APIRouter, HTTPException
from typing import List
from pydantic import BaseModel, Field

from app.chat.model import ChatDto
from app.chat.service import chat_service
from app.file.model import SourceFileDto
from app.file.rag_service import rag_service
from app.generated_content.exam_service import exam_service
from app.generated_content.flashcard_service import flashcard_service
from app.generated_content.model import ExamDto, FlashcardDto
from app.workspace.model import WorkspaceDto
from app.workspace.service import workspace_service

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


class CreateWorkspaceRequest(BaseModel):
    name: str = Field(..., alias="name")


@router.post("", response_model=WorkspaceDto, status_code=201)
async def create_workspace(payload: CreateWorkspaceRequest):
    """Create a new workspace"""

    try:
        return await workspace_service.create_workspace(payload.name)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=List[WorkspaceDto])
async def list_workspaces():
    """List all workspaces with pagination"""

    try:
        return await workspace_service.get_all()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{workspace_id}", response_model=WorkspaceDto)
async def get_workspace(workspace_id: str):
    """Get workspace by ID"""

    try:
        workspace = await workspace_service.get_workspace_by_id(workspace_id)
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")

        return workspace
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{workspace_id}", status_code=204)
async def delete_workspace(workspace_id: str):
    """Delete a workspace"""

    try:
        deleted = await workspace_service.delete_workspace(workspace_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Workspace not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{workspace_id}/chats")
async def get_workspace_chats(workspace_id: str) -> List[ChatDto]:
    """Get all chats for a workspace"""

    try:
        return await chat_service.get_chats_by_workspace_id(workspace_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{workspace_id}/flashcards", response_model=List[FlashcardDto])
async def get_workspace_flashcards(workspace_id: str):
    """Get all flashcards for a workspace"""

    try:
        return await flashcard_service.get_flashcards_by_workspace_id(
            workspace_id=workspace_id,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{workspace_id}/exams", response_model=List[ExamDto])
async def get_workspace_exams(workspace_id: str):
    """Get all exams for a workspace"""

    try:
        return await exam_service.get_exams_by_workspace_id(workspace_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{workspace_id}/files", response_model=List[SourceFileDto])
async def get_workspace_files(workspace_id: str):
    """Get all files for a workspace"""

    try:
        return await rag_service.get_source_files_by_workspace_id(workspace_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
