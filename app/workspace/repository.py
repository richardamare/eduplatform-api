# pyrefly: ignore-all-errors

import logging
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from datetime import datetime
from typing import Optional, List

from app.workspace.db import WorkspaceDB


logger = logging.getLogger(__name__)


class WorkspaceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, payload: WorkspaceDB) -> WorkspaceDB:
        try:
            workspace = WorkspaceDB(
                id=uuid.uuid4(),
                name=payload.name,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            self.db.add(workspace)
            await self.db.commit()
            await self.db.refresh(workspace)
            return workspace
        except Exception as e:
            logger.error(f"Error creating workspace: {e}")
            raise e

    async def get_by_id(self, workspace_id: str) -> Optional[WorkspaceDB]:
        try:
            result = await self.db.execute(
                select(WorkspaceDB).where(WorkspaceDB.id == workspace_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting workspace by id: {e}")
            raise e

    async def get_all(self) -> List[WorkspaceDB]:
        try:
            result = await self.db.execute(select(WorkspaceDB))
            workspaces = result.scalars().all()
            return [
                WorkspaceDB(
                    id=workspace.id,
                    name=workspace.name,
                    created_at=workspace.created_at,
                    updated_at=workspace.updated_at,
                )
                for workspace in workspaces
            ]
        except Exception as e:
            logger.error(f"Error getting all workspaces: {e}")
            raise e

    async def delete(self, workspace_id: str):
        try:
            await self.db.execute(
                delete(WorkspaceDB).where(WorkspaceDB.id == workspace_id)
            )
            await self.db.commit()
        except Exception as e:
            logger.error(f"Error deleting workspace: {e}")
            raise e
