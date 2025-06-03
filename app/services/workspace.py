from datetime import datetime
from typing import List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.workspace import Workspace, CreateWorkspacePayload, WorkspaceDto
from app.models.db_models import WorkspaceDB
from app.database import get_db


class WorkspaceService:
    """Service for workspace operations"""
    
    def __init__(self):
        pass
    
    async def create_workspace(self, payload: CreateWorkspacePayload, db: AsyncSession) -> WorkspaceDto:
        """Create a new workspace"""
        workspace_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        # Create database record
        workspace_db = WorkspaceDB(
            id=workspace_id,
            name=payload.name,
            created_at=now,
            updated_at=now
        )
        
        db.add(workspace_db)
        await db.commit()
        await db.refresh(workspace_db)
        
        return WorkspaceDto(
            id=workspace_db.id,
            name=workspace_db.name,
            created_at=workspace_db.created_at,
            updated_at=workspace_db.updated_at
        )
    
    async def get_workspace(self, workspace_id: str, db: AsyncSession) -> Optional[WorkspaceDto]:
        """Get workspace by ID"""
        result = await db.execute(
            select(WorkspaceDB).where(WorkspaceDB.id == workspace_id)
        )
        workspace = result.scalar_one_or_none()
        
        if not workspace:
            return None
        
        return WorkspaceDto(
            id=workspace.id,
            name=workspace.name,
            created_at=workspace.created_at,
            updated_at=workspace.updated_at
        )
    
    async def list_workspaces(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[WorkspaceDto]:
        """List all workspaces with pagination"""
        result = await db.execute(
            select(WorkspaceDB).offset(skip).limit(limit)
        )
        workspaces = result.scalars().all()
        
        return [
            WorkspaceDto(
                id=workspace.id,
                name=workspace.name,
                created_at=workspace.created_at,
                updated_at=workspace.updated_at
            )
            for workspace in workspaces
        ]

    async def update_workspace(self, workspace_id: str, payload: CreateWorkspacePayload, db: AsyncSession) -> Optional[WorkspaceDto]:
        """Update an existing workspace"""
        result = await db.execute(
            select(WorkspaceDB).where(WorkspaceDB.id == workspace_id)
        )
        workspace = result.scalar_one_or_none()
        
        if not workspace:
            return None
        
        workspace.name = payload.name
        workspace.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(workspace)
        
        return WorkspaceDto(
            id=workspace.id,
            name=workspace.name,
            created_at=workspace.created_at,
            updated_at=workspace.updated_at
        )

    async def delete_workspace(self, workspace_id: str, db: AsyncSession) -> bool:
        """Delete a workspace"""
        result = await db.execute(
            select(WorkspaceDB).where(WorkspaceDB.id == workspace_id)
        )
        workspace = result.scalar_one_or_none()
        
        if not workspace:
            return False
        
        await db.delete(workspace)
        await db.commit()
        return True


# Global instance
workspace_service = WorkspaceService() 