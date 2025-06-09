import logging
from typing import List, Optional

from app.database import async_session
from app.workspace.db import WorkspaceDB
from app.workspace.model import WorkspaceDto
from app.workspace.repository import WorkspaceRepository


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WorkspaceService:
    """Service for workspace operations"""

    def __init__(self):
        self.repository = WorkspaceRepository(async_session())

    async def create_workspace(self, name: str) -> WorkspaceDto:
        """Create a new workspace"""
        try:
            workspace = await self.repository.create(
                WorkspaceDB(
                    name=name,
                )
            )

            return self._map_to_workspace_dto(workspace)
        except Exception as e:
            logger.error(f"Error creating workspace: {e}")
            raise e

    async def get_workspace_by_id(self, workspace_id: str) -> Optional[WorkspaceDto]:
        """Get workspace by ID"""
        workspace = await self.repository.get_by_id(workspace_id)

        if not workspace:
            return None

        return self._map_to_workspace_dto(workspace)

    async def get_all(self) -> List[WorkspaceDto]:
        """List all workspaces with pagination"""
        workspaces = await self.repository.get_all()

        return [self._map_to_workspace_dto(workspace) for workspace in workspaces]

    async def delete_workspace(self, workspace_id: str):
        """Delete a workspace"""

        await self.repository.delete(workspace_id)

    def _map_to_workspace_dto(self, workspace: WorkspaceDB) -> WorkspaceDto:
        return WorkspaceDto(
            id=str(workspace.id),
            name=workspace.name,
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
        )


# Global instance
workspace_service = WorkspaceService()
