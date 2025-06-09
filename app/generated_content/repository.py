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
        try:
            data_item = GeneratedContentDB(
                id=uuid.uuid4(),
                type=payload.type,
                content=payload.content,
                workspace_id=payload.workspace_id,
            )
            self.db.add(data_item)
            await self.db.commit()
            await self.db.refresh(data_item)
            return data_item
        except Exception as e:
            logger.error(f"Error creating exam: {e}")
            raise e

    async def get_by_workspace_id(self, workspace_id: str) -> List[GeneratedContentDB]:
        try:
            result = await self.db.execute(
                select(GeneratedContentDB)
                .where(GeneratedContentDB.workspace_id == workspace_id)
                .where(GeneratedContentDB.type == "exam")
            )
            data_items = result.scalars().all()
            return [
                GeneratedContentDB(
                    id=data_item.id,
                    type=data_item.type,
                    content=data_item.content,
                    workspace_id=data_item.workspace_id,
                )
                for data_item in data_items
            ]
        except Exception as e:
            logger.error(f"Error getting exams by workspace id: {e}")
            raise e

    async def get_by_id(
        self, generated_content_id: str
    ) -> Optional[GeneratedContentDB]:
        try:
            result = await self.db.execute(
                select(GeneratedContentDB).where(
                    GeneratedContentDB.id == generated_content_id
                )
            )
            data_item = result.scalar_one_or_none()
            return (
                GeneratedContentDB(
                    id=data_item.id,
                    type=data_item.type,
                    content=data_item.content,
                    workspace_id=data_item.workspace_id,
                )
                if data_item
                else None
            )
        except Exception as e:
            logger.error(f"Error getting exam by id: {e}")
            raise e


class FlashcardRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, payload: GeneratedContentDB) -> GeneratedContentDB:
        try:
            data_item = GeneratedContentDB(
                id=uuid.uuid4(),
                type=payload.type,
                content=payload.content,
                workspace_id=payload.workspace_id,
            )
            self.db.add(data_item)
            await self.db.commit()
            await self.db.refresh(data_item)
            return data_item
        except Exception as e:
            logger.error(f"Error creating flashcard: {e}")
            raise e

    async def get_by_workspace_id(self, workspace_id: str) -> List[GeneratedContentDB]:
        try:
            result = await self.db.execute(
                select(GeneratedContentDB)
                .where(GeneratedContentDB.workspace_id == workspace_id)
                .where(GeneratedContentDB.type == "flashcard")
            )
            data_items = result.scalars().all()
            return [
                GeneratedContentDB(
                    id=data_item.id,
                    type=data_item.type,
                    content=data_item.content,
                    workspace_id=data_item.workspace_id,
                )
                for data_item in data_items
            ]
        except Exception as e:
            logger.error(f"Error getting flashcards by workspace id: {e}")
            raise e

    async def get_by_id(
        self, generated_content_id: str
    ) -> Optional[GeneratedContentDB]:
        try:
            result = await self.db.execute(
                select(GeneratedContentDB).where(
                    GeneratedContentDB.id == generated_content_id
                )
            )
            data_item = result.scalar_one_or_none()
            return (
                GeneratedContentDB(
                    id=data_item.id,
                    type=data_item.type,
                    content=data_item.content,
                    workspace_id=data_item.workspace_id,
                )
                if data_item
                else None
            )
        except Exception as e:
            logger.error(f"Error getting flashcard by id: {e}")
            raise e
