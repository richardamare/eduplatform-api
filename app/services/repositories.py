from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func, text
from sqlalchemy.orm import selectinload
from typing import List, Optional, Tuple
import uuid
from datetime import datetime

from app.models.db_models import ChatDB, MessageDB, WorkspaceDB, AttachmentDB
from app.models.chat import Chat, ChatDto
from app.models.message import Message, MessageDto, CreateMessagePayload
from app.models.workspace import Workspace, WorkspaceDto, CreateWorkspacePayload
from app.models.attachment import Attachment, AttachmentDto, CreateAttachmentPayload, AttachmentSearchResult

class WorkspaceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, payload: CreateWorkspacePayload) -> WorkspaceDto:
        workspace = WorkspaceDB(
            id=str(uuid.uuid4()),
            name=payload.name,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        self.db.add(workspace)
        await self.db.commit()
        await self.db.refresh(workspace)
        return WorkspaceDto(**workspace.__dict__)

    async def get_by_id(self, workspace_id: str) -> Optional[WorkspaceDto]:
        result = await self.db.execute(select(WorkspaceDB).where(WorkspaceDB.id == workspace_id))
        workspace = result.scalar_one_or_none()
        return WorkspaceDto(**workspace.__dict__) if workspace else None

    async def get_all(self) -> List[WorkspaceDto]:
        result = await self.db.execute(select(WorkspaceDB))
        workspaces = result.scalars().all()
        return [WorkspaceDto(**workspace.__dict__) for workspace in workspaces]

    async def delete(self, workspace_id: str) -> bool:
        result = await self.db.execute(delete(WorkspaceDB).where(WorkspaceDB.id == workspace_id))
        await self.db.commit()
        return result.rowcount > 0

class ChatRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, name: str, workspace_id: str) -> ChatDto:
        chat = ChatDB(
            id=str(uuid.uuid4()),
            name=name,
            workspace_id=workspace_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        self.db.add(chat)
        await self.db.commit()
        await self.db.refresh(chat)
        return ChatDto(**chat.__dict__)

    async def get_by_id(self, chat_id: str) -> Optional[ChatDto]:
        result = await self.db.execute(select(ChatDB).where(ChatDB.id == chat_id))
        chat = result.scalar_one_or_none()
        return ChatDto(**chat.__dict__) if chat else None

    async def get_by_workspace(self, workspace_id: str) -> List[ChatDto]:
        result = await self.db.execute(select(ChatDB).where(ChatDB.workspace_id == workspace_id))
        chats = result.scalars().all()
        return [ChatDto(**chat.__dict__) for chat in chats]

    async def update_name(self, chat_id: str, name: str) -> bool:
        result = await self.db.execute(select(ChatDB).where(ChatDB.id == chat_id))
        chat = result.scalar_one_or_none()
        if chat:
            chat.name = name
            chat.updated_at = datetime.utcnow()
            await self.db.commit()
            return True
        return False

    async def delete(self, chat_id: str) -> bool:
        result = await self.db.execute(delete(ChatDB).where(ChatDB.id == chat_id))
        await self.db.commit()
        return result.rowcount > 0

class MessageRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, chat_id: str, payload: CreateMessagePayload) -> MessageDto:
        message = MessageDB(
            id=str(uuid.uuid4()),
            chat_id=chat_id,
            role=payload.role.value,
            content=payload.content,
            created_at=datetime.utcnow()
        )
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        return MessageDto(**message.__dict__)

    async def get_by_chat(self, chat_id: str) -> List[MessageDto]:
        result = await self.db.execute(
            select(MessageDB)
            .where(MessageDB.chat_id == chat_id)
            .order_by(MessageDB.created_at)
        )
        messages = result.scalars().all()
        return [MessageDto(**message.__dict__) for message in messages]

    async def count_by_chat(self, chat_id: str) -> int:
        result = await self.db.execute(
            select(func.count(MessageDB.id))
            .where(MessageDB.chat_id == chat_id)
        )
        return result.scalar()

class AttachmentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, payload: CreateAttachmentPayload) -> AttachmentDto:
        attachment = AttachmentDB(
            id=str(uuid.uuid4()),
            name=payload.name,
            type=payload.type,
            azure_blob_path=payload.azure_blob_path,
            workspace_id=payload.workspace_id,
            content_vector=payload.content_vector,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        self.db.add(attachment)
        await self.db.commit()
        await self.db.refresh(attachment)
        return AttachmentDto(**attachment.__dict__)

    async def get_by_id(self, attachment_id: str) -> Optional[AttachmentDto]:
        result = await self.db.execute(select(AttachmentDB).where(AttachmentDB.id == attachment_id))
        attachment = result.scalar_one_or_none()
        return AttachmentDto(**attachment.__dict__) if attachment else None

    async def get_by_workspace(self, workspace_id: str) -> List[AttachmentDto]:
        result = await self.db.execute(select(AttachmentDB).where(AttachmentDB.workspace_id == workspace_id))
        attachments = result.scalars().all()
        return [AttachmentDto(**attachment.__dict__) for attachment in attachments]

    async def update_vector(self, attachment_id: str, vector: List[float]) -> bool:
        result = await self.db.execute(
            select(AttachmentDB).where(AttachmentDB.id == attachment_id)
        )
        attachment = result.scalar_one_or_none()
        if attachment:
            attachment.content_vector = vector
            attachment.updated_at = datetime.utcnow()
            await self.db.commit()
            return True
        return False

    async def vector_similarity_search(
        self, 
        query_vector: List[float], 
        workspace_id: str, 
        limit: int = 10,
        similarity_threshold: float = 0.7
    ) -> List[AttachmentSearchResult]:
        """Search for similar attachments using cosine similarity"""
        query = text("""
            SELECT id, name, type, azure_blob_path, workspace_id, content_vector, 
                   created_at, updated_at,
                   1 - (content_vector <=> :query_vector) as similarity
            FROM attachments 
            WHERE workspace_id = :workspace_id 
                AND content_vector IS NOT NULL
                AND 1 - (content_vector <=> :query_vector) > :threshold
            ORDER BY content_vector <=> :query_vector
            LIMIT :limit
        """)
        
        result = await self.db.execute(
            query,
            {
                "query_vector": str(query_vector),
                "workspace_id": workspace_id,
                "threshold": similarity_threshold,
                "limit": limit
            }
        )
        
        rows = result.fetchall()
        results = []
        
        for row in rows:
            attachment_dto = AttachmentDto(
                id=row.id,
                name=row.name,
                type=row.type,
                azure_blob_path=row.azure_blob_path,
                workspace_id=row.workspace_id,
                content_vector=row.content_vector,
                created_at=row.created_at,
                updated_at=row.updated_at
            )
            results.append(AttachmentSearchResult(
                attachment=attachment_dto,
                similarity_score=row.similarity
            ))
        
        return results

    async def delete(self, attachment_id: str) -> bool:
        # First get the attachment to retrieve the blob path
        result = await self.db.execute(select(AttachmentDB).where(AttachmentDB.id == attachment_id))
        attachment = result.scalar_one_or_none()
        
        if not attachment:
            return False
        
        # Delete from Azure Blob Storage
        from app.services.azure_blob_service import azure_blob_service
        azure_blob_service.delete_blob(attachment.azure_blob_path)
        
        # Delete from database
        result = await self.db.execute(delete(AttachmentDB).where(AttachmentDB.id == attachment_id))
        await self.db.commit()
        return result.rowcount > 0 