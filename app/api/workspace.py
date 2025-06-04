from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.models.flashcard import FlashcardDto
from app.models.workspace import CreateWorkspacePayload, WorkspaceDto
from app.models.rag import SourceFileDto
from app.services.flashcard_service import flashcard_service
from app.services.workspace import workspace_service
from app.services.repositories import ChatRepository
from app.models.chat import ChatDto
from app.database import get_db
from app.services.exam_service import exam_service
from app.models.exam import ExamDto
from app.services.rag_service import RAGService

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post("", response_model=WorkspaceDto, status_code=201)
async def create_workspace(
    payload: CreateWorkspacePayload, 
    db: AsyncSession = Depends(get_db)
):
    """Create a new workspace"""
    try:
        workspace = await workspace_service.create_workspace(payload, db)
        return workspace
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=List[WorkspaceDto])
async def list_workspaces(
    skip: int = Query(0, ge=0, description="Number of workspaces to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of workspaces to return"),
    db: AsyncSession = Depends(get_db)
):
    """List all workspaces with pagination"""
    try:
        workspaces = await workspace_service.list_workspaces(db, skip=skip, limit=limit)
        return workspaces
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{workspace_id}", response_model=WorkspaceDto)
async def get_workspace(
    workspace_id: str, 
    db: AsyncSession = Depends(get_db)
):
    """Get workspace by ID"""
    try:
        workspace = await workspace_service.get_workspace(workspace_id, db)
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")
        
        return workspace
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{workspace_id}", response_model=WorkspaceDto)
async def update_workspace(
    workspace_id: str,
    payload: CreateWorkspacePayload,
    db: AsyncSession = Depends(get_db)
):
    """Update an existing workspace"""
    try:
        workspace = await workspace_service.update_workspace(workspace_id, payload, db)
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")
        
        return workspace
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{workspace_id}", status_code=204)
async def delete_workspace(
    workspace_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a workspace"""
    try:
        deleted = await workspace_service.delete_workspace(workspace_id, db)
        if not deleted:
            raise HTTPException(status_code=404, detail="Workspace not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 

@router.get("/{workspace_id}/chats")
async def get_workspace_chats(workspace_id: str, db: AsyncSession = Depends(get_db)) -> List[ChatDto]:
    """Get all chats for a workspace"""
    chat_repo = ChatRepository(db)
    return await chat_repo.get_by_workspace(workspace_id)


@router.get("/{workspace_id}/flashcards", response_model=List[FlashcardDto])
async def get_workspace_flashcards(workspace_id: str):
    """Get all flashcards for a workspace"""

    try:
        flashcards = await flashcard_service.get_saved_flashcards(
            workspace_id=workspace_id,
        )
        return flashcards
        
    except Exception as e:
        print(f"Error in get_saved_flashcards endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve saved flashcards."
        ) 


@router.get("/{workspace_id}/exams", response_model=List[ExamDto])
async def get_workspace_exams(workspace_id: str):
    """Get all exams for a workspace"""
    try:
        exams = await exam_service.get_saved_exams(workspace_id)
        return exams
    except Exception as e:
        print(f"Error in get_saved_exams endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve saved exams."
        )

@router.get("/{workspace_id}/files", response_model=List[SourceFileDto])
async def get_workspace_files(workspace_id: str, db: AsyncSession = Depends(get_db)):
    """Get all files for a workspace"""
    try:
        rag_service = RAGService()
        files = await rag_service.get_workspace_source_files(db, workspace_id)
        return files
    except Exception as e:
        print(f"Error in get_workspace_files endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))