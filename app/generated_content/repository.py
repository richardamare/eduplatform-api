# pyrefly: ignore-all-errors

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import uuid

from app.generated_content.db import GeneratedContentDB


class ExamRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, payload: GeneratedContentDB) -> GeneratedContentDB:
        data_item = GeneratedContentDB(
            id=str(uuid.uuid4()),
            type=payload.type,
            content=payload.content,
            workspace_id=payload.workspace_id,
        )
        self.db.add(data_item)
        await self.db.commit()
        await self.db.refresh(data_item)
        return data_item

    async def get_by_workspace_id(self, workspace_id: str) -> List[GeneratedContentDB]:
        result = await self.db.execute(
            select(GeneratedContentDB)
            .where(GeneratedContentDB.workspace_id == workspace_id)
            .where(GeneratedContentDB.type == "exam")
        )
        data_items = result.scalars().all()
        return [GeneratedContentDB(**data_item.__dict__) for data_item in data_items]

    async def get_by_id(
        self, generated_content_id: str
    ) -> Optional[GeneratedContentDB]:
        result = await self.db.execute(
            select(GeneratedContentDB).where(
                GeneratedContentDB.id == generated_content_id
            )
        )
        data_item = result.scalar_one_or_none()
        return GeneratedContentDB(**data_item.__dict__) if data_item else None


class FlashcardRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, payload: GeneratedContentDB) -> GeneratedContentDB:
        data_item = GeneratedContentDB(
            id=str(uuid.uuid4()),
            type=payload.type,
            content=payload.content,
            workspace_id=payload.workspace_id,
        )
        self.db.add(data_item)
        await self.db.commit()
        await self.db.refresh(data_item)
        return data_item

    async def get_by_workspace_id(self, workspace_id: str) -> List[GeneratedContentDB]:
        result = await self.db.execute(
            select(GeneratedContentDB)
            .where(GeneratedContentDB.workspace_id == workspace_id)
            .where(GeneratedContentDB.type == "flashcard")
        )
        data_items = result.scalars().all()
        return [GeneratedContentDB(**data_item.__dict__) for data_item in data_items]

    async def get_by_id(
        self, generated_content_id: str
    ) -> Optional[GeneratedContentDB]:
        result = await self.db.execute(
            select(GeneratedContentDB).where(
                GeneratedContentDB.id == generated_content_id
            )
        )
        data_item = result.scalar_one_or_none()
        return GeneratedContentDB(**data_item.__dict__) if data_item else None
