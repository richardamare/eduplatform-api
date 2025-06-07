# pyrefly: ignore-all-errors

import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from datetime import datetime, timezone
from typing import Optional, List

from app.models.db_models import WorkspaceDB
from app.workspace.model import WorkspaceDto


class WorkspaceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, payload: WorkspaceDB) -> WorkspaceDB:
        workspace = WorkspaceDB(
            id=str(uuid.uuid4()),
            name=payload.name,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.db.add(workspace)
        await self.db.commit()
        await self.db.refresh(workspace)
        return workspace

    async def get_by_id(self, workspace_id: str) -> Optional[WorkspaceDto]:
        result = await self.db.execute(
            select(WorkspaceDB).where(WorkspaceDB.id == workspace_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self) -> List[WorkspaceDB]:
        result = await self.db.execute(select(WorkspaceDB))
        workspaces = result.scalars().all()
        return [WorkspaceDB(**workspace.__dict__) for workspace in workspaces]

    async def delete(self, workspace_id: str):
        await self.db.execute(delete(WorkspaceDB).where(WorkspaceDB.id == workspace_id))
        await self.db.commit()
