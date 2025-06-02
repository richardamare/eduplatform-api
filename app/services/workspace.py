from datetime import datetime
from typing import List, Optional
import uuid

from app.models.workspace import Workspace, CreateWorkspacePayload, WorkspaceDto


class WorkspaceService:
    """Service for workspace operations"""
    
    def __init__(self):
        # In-memory storage for now - replace with database later
        self._workspaces = {}
    
    async def create_workspace(self, payload: CreateWorkspacePayload) -> WorkspaceDto:
        """Create a new workspace"""
        workspace_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        workspace = Workspace(
            id=workspace_id,
            name=payload.name,
            created_at=now,
            updated_at=now
        )
        
        self._workspaces[workspace_id] = workspace
        
        return WorkspaceDto(
            id=workspace.id,
            name=workspace.name,
            created_at=workspace.created_at,
            updated_at=workspace.updated_at
        )
    
    async def get_workspace(self, workspace_id: str) -> Optional[WorkspaceDto]:
        """Get workspace by ID"""
        workspace = self._workspaces.get(workspace_id)
        if not workspace:
            return None
        
        return WorkspaceResponse(
            id=workspace.id,
            name=workspace.name,
            created_at=workspace.created_at,
            updated_at=workspace.updated_at
        )
    
    async def list_workspaces(self, skip: int = 0, limit: int = 100) -> List[WorkspaceDto]:
        """List all workspaces with pagination"""
        workspaces = list(self._workspaces.values())
        
        # Apply pagination
        paginated_workspaces = workspaces[skip:skip + limit]
        
        return [
            WorkspaceResponse(
                id=workspace.id,
                name=workspace.name,
                created_at=workspace.created_at,
                updated_at=workspace.updated_at
            )
            for workspace in paginated_workspaces
        ]



# Global instance
workspace_service = WorkspaceService() 