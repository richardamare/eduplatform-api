from fastapi import APIRouter, HTTPException, Query
from typing import List

from app.models.workspace import CreateWorkspacePayload, WorkspaceDto
from app.services.workspace import workspace_service

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post("", response_model=WorkspaceDto, status_code=201)
async def create_workspace(payload: CreateWorkspacePayload):
    """Create a new workspace"""
    try:
        workspace = await workspace_service.create_workspace(payload)
        return workspace
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=List[WorkspaceDto])
async def list_workspaces(
    skip: int = Query(0, ge=0, description="Number of workspaces to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of workspaces to return")
):
    """List all workspaces with pagination"""
    try:
        workspaces = await workspace_service.list_workspaces(skip=skip, limit=limit)
        
        return workspaces
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{workspace_id}", response_model=WorkspaceDto)
async def get_workspace(workspace_id: str):
    """Get workspace by ID"""
    try:
        workspace = await workspace_service.get_workspace(workspace_id)
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")
        
        return workspace
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 