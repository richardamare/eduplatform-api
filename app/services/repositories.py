# pyrefly: ignore-all-errors

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func, text
from typing import List, Optional
import uuid
from datetime import datetime, timezone

from app.models.db_models import (
    ChatDB,
    DataItemDB,
    MessageDB,
    WorkspaceDB,
)
from app.models.rag import VectorSearchResult
from app.models.rag_models import SourceFileDB, VectorDB
from app.models.workspace import WorkspaceDto


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


class ChatRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, name: str, workspace_id: str) -> ChatDB:
        chat = ChatDB(
            id=str(uuid.uuid4()),
            name=name,
            workspace_id=workspace_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.db.add(chat)
        await self.db.commit()
        await self.db.refresh(chat)
        return chat

    async def get_by_id(self, chat_id: str) -> Optional[ChatDB]:
        result = await self.db.execute(select(ChatDB).where(ChatDB.id == chat_id))
        chat = result.scalar_one_or_none()
        return ChatDB(**chat.__dict__) if chat else None

    async def get_by_workspace(self, workspace_id: str) -> List[ChatDB]:
        result = await self.db.execute(
            select(ChatDB).where(ChatDB.workspace_id == workspace_id)
        )
        all_chats = result.scalars().all()
        return [ChatDB(**chat.__dict__) for chat in all_chats]

    async def update_name(self, chat_id: str, name: str) -> bool:
        result = await self.db.execute(select(ChatDB).where(ChatDB.id == chat_id))
        chat = result.scalar_one_or_none()
        if chat:
            chat.name = name
            chat.updated_at = datetime.utcnow()
            await self.db.commit()
            return True
        return False

    async def delete(self, chat_id: str):
        await self.db.execute(delete(ChatDB).where(ChatDB.id == chat_id))
        await self.db.commit()


class MessageRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, payload: MessageDB) -> MessageDB:
        message = MessageDB(
            id=str(uuid.uuid4()),
            chat_id=payload.chat_id,
            role=payload.role,
            content=payload.content,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        return message

    async def get_by_chat_id(self, chat_id: str) -> List[MessageDB]:
        result = await self.db.execute(
            select(MessageDB)
            .where(MessageDB.chat_id == chat_id)
            .order_by(MessageDB.created_at)
        )
        messages = result.scalars().all()
        return [MessageDB(**message.__dict__) for message in messages]

    async def count_by_chat(self, chat_id: str) -> int:
        result = await self.db.execute(
            select(func.count(MessageDB.id)).where(MessageDB.chat_id == chat_id)
        )
        sc = result.scalar()
        if sc is None:
            return 0
        return sc


class ExamRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, payload: DataItemDB) -> DataItemDB:
        data_item = DataItemDB(
            id=str(uuid.uuid4()),
            type=payload.type,
            content=payload.content,
            workspace_id=payload.workspace_id,
        )
        self.db.add(data_item)
        await self.db.commit()
        await self.db.refresh(data_item)
        return data_item

    async def get_by_workspace(self, workspace_id: str) -> List[DataItemDB]:
        result = await self.db.execute(
            select(DataItemDB)
            .where(DataItemDB.workspace_id == workspace_id)
            .where(DataItemDB.type == "exam")
        )
        data_items = result.scalars().all()
        return [DataItemDB(**data_item.__dict__) for data_item in data_items]

    async def get_by_id(self, data_item_id: str) -> Optional[DataItemDB]:
        result = await self.db.execute(
            select(DataItemDB).where(DataItemDB.id == data_item_id)
        )
        data_item = result.scalar_one_or_none()
        return DataItemDB(**data_item.__dict__) if data_item else None


class FlashcardRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, payload: DataItemDB) -> DataItemDB:
        data_item = DataItemDB(
            id=str(uuid.uuid4()),
            type=payload.type,
            content=payload.content,
            workspace_id=payload.workspace_id,
        )
        self.db.add(data_item)
        await self.db.commit()
        await self.db.refresh(data_item)
        return data_item

    async def get_by_workspace(self, workspace_id: str) -> List[DataItemDB]:
        result = await self.db.execute(
            select(DataItemDB)
            .where(DataItemDB.workspace_id == workspace_id)
            .where(DataItemDB.type == "flashcard")
        )
        data_items = result.scalars().all()
        return [DataItemDB(**data_item.__dict__) for data_item in data_items]

    async def get_by_id(self, data_item_id: str) -> Optional[DataItemDB]:
        result = await self.db.execute(
            select(DataItemDB).where(DataItemDB.id == data_item_id)
        )
        data_item = result.scalar_one_or_none()
        return DataItemDB(**data_item.__dict__) if data_item else None


class SourceFileRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, payload: SourceFileDB) -> SourceFileDB:
        source_file = SourceFileDB(
            id=str(uuid.uuid4()),
            file_path=payload.file_path,
            file_name=payload.file_name,
            content_type=payload.content_type,
            workspace_id=payload.workspace_id,
            file_size=payload.file_size,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.db.add(source_file)
        await self.db.commit()
        await self.db.refresh(source_file)
        return source_file

    async def get_by_workspace(self, workspace_id: str) -> List[SourceFileDB]:
        result = await self.db.execute(
            select(SourceFileDB).where(SourceFileDB.workspace_id == workspace_id)
        )
        source_files = result.scalars().all()
        return [SourceFileDB(**source_file.__dict__) for source_file in source_files]

    async def get_by_id(self, source_file_id: str) -> Optional[SourceFileDB]:
        result = await self.db.execute(
            select(SourceFileDB).where(SourceFileDB.id == source_file_id)
        )
        source_file = result.scalar_one_or_none()
        return SourceFileDB(**source_file.__dict__) if source_file else None

    async def delete_by_file_path(self, file_path: str):
        delete_vectors_stmt = text(
            """
            DELETE FROM vectors 
            WHERE source_file_id IN (
                SELECT id FROM source_files WHERE file_path = :file_path
            )
        """
        )

        delete_source_file_stmt = text(
            """
            DELETE FROM source_files WHERE file_path = :file_path
        """
        )

        await self.db.execute(delete_vectors_stmt, {"file_path": file_path})
        await self.db.execute(delete_source_file_stmt, {"file_path": file_path})
        await self.db.commit()

    async def get_by_file_path(self, file_path: str) -> Optional[SourceFileDB]:
        result = await self.db.execute(
            select(SourceFileDB).where(SourceFileDB.file_path == file_path)
        )
        source_file = result.scalar_one_or_none()
        return SourceFileDB(**source_file.__dict__) if source_file else None

    async def exists(self, file_path: str) -> bool:
        stmt = select(SourceFileDB).where(SourceFileDB.file_path == file_path)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_all(self) -> List[SourceFileDB]:
        result = await self.db.execute(select(SourceFileDB))
        source_files = result.scalars().all()
        return [SourceFileDB(**source_file.__dict__) for source_file in source_files]


class VectorRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, payload: VectorDB) -> VectorDB:
        vector = VectorDB(
            id=str(uuid.uuid4()),
            source_file_id=payload.source_file_id,
            vector_data=payload.vector_data,
            content_text=payload.content_text,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(vector)
        await self.db.commit()
        await self.db.refresh(vector)
        return vector

    async def get_by_source_file(self, source_file_id: str) -> List[VectorDB]:
        result = await self.db.execute(
            select(VectorDB).where(VectorDB.source_file_id == source_file_id)
        )
        vectors = result.scalars().all()
        return [VectorDB(**vector.__dict__) for vector in vectors]

    async def delete_by_source_file(self, source_file_id: str):
        await self.db.execute(
            delete(VectorDB).where(VectorDB.source_file_id == source_file_id)
        )
        await self.db.commit()

    async def search_similar_vectors(
        self,
        query_embedding: List[float],
        workspace_id: Optional[str] = None,
        limit: int = 5,
        min_similarity: float = 0.0,
    ) -> List[VectorSearchResult]:
        """Search for similar vectors using cosine similarity."""

        # Build SQL with optional workspace filter
        where_clause = f"WHERE cosine_similarity(v.vector_data, '{query_embedding}'::vector) >= {min_similarity}"
        if workspace_id:
            where_clause += f" AND sf.workspace_id = '{workspace_id}'"

        sql = text(
            f"""
            SELECT 
                v.id,
                v.content_text,
                sf.file_path,
                sf.file_name,
                cosine_similarity(v.vector_data, '{query_embedding}'::vector) as similarity
            FROM vectors v
            JOIN source_files sf ON v.source_file_id = sf.id
            {where_clause}
            ORDER BY similarity DESC
            LIMIT {limit}
        """
        )

        result = await self.db.execute(sql)

        search_results = [
            VectorSearchResult(
                vector_id=row.id,
                similarity=row.similarity,
                content_text=row.content_text,
                file_path=row.file_path,
            )
            for row in result
        ]

        return search_results

    async def get_vector_count_by_file_path(self, file_path: str) -> int:
        sql = text(
            """
            SELECT COUNT(v.id) 
            FROM vectors v
            JOIN source_files sf ON v.source_file_id = sf.id
            WHERE sf.file_path = :file_path
        """
        )
        result = await self.db.execute(sql, {"file_path": file_path})
        sc = result.scalar()
        if sc is None:
            return 0
        return sc
