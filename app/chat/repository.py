# pyrefly: ignore-all-errors

import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from datetime import datetime, timezone
from typing import Optional, List

from app.chat.db import ChatDB


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
