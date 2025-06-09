# pyrefly: ignore-all-errors

import uuid
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from datetime import datetime, timezone
from typing import Optional, List

from app.chat.db import ChatDB, MessageDB

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChatRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, name: str, workspace_id: uuid.UUID) -> ChatDB:
        try:
            chat = ChatDB(
                id=uuid.uuid4(),
                name=name,
                workspace_id=workspace_id,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            self.db.add(chat)
            await self.db.commit()
            await self.db.refresh(chat)
            return chat
        except Exception as e:
            logger.error(f"Error creating chat: {e}")
            raise e

    async def get_by_id(self, chat_id: uuid.UUID) -> Optional[ChatDB]:
        try:
            result = await self.db.execute(select(ChatDB).where(ChatDB.id == chat_id))
            chat = result.scalar_one_or_none()
            return (
                ChatDB(
                    id=chat.id,
                    name=chat.name,
                    workspace_id=chat.workspace_id,
                    created_at=chat.created_at,
                    updated_at=chat.updated_at,
                )
                if chat
                else None
            )
        except Exception as e:
            logger.error(f"Error getting chat by id: {e}")
            raise e

    async def get_by_workspace(self, workspace_id: uuid.UUID) -> List[ChatDB]:
        try:
            result = await self.db.execute(
                select(ChatDB).where(ChatDB.workspace_id == workspace_id)
            )
            all_chats = result.scalars().all()
            return [
                ChatDB(
                    id=chat.id,
                    name=chat.name,
                    workspace_id=chat.workspace_id,
                    created_at=chat.created_at,
                    updated_at=chat.updated_at,
                )
                for chat in all_chats
            ]
        except Exception as e:
            logger.error(f"Error getting chats by workspace: {e}")
            raise e

    async def update_name(self, chat_id: uuid.UUID, name: str) -> bool:
        try:
            result = await self.db.execute(select(ChatDB).where(ChatDB.id == chat_id))
            chat = result.scalar_one_or_none()
            if chat:
                chat.name = name
                chat.updated_at = datetime.now()
                await self.db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating chat name: {e}")
            raise e

    async def delete(self, chat_id: uuid.UUID):
        try:
            await self.db.execute(delete(ChatDB).where(ChatDB.id == chat_id))
            await self.db.commit()
        except Exception as e:
            logger.error(f"Error deleting chat: {e}")
            raise e


class MessageRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, payload: MessageDB) -> MessageDB:
        try:
            message = MessageDB(
                id=uuid.uuid4(),
                chat_id=payload.chat_id,
                role=payload.role,
                content=payload.content,
                created_at=datetime.now(),
            )
            self.db.add(message)
            await self.db.commit()
            await self.db.refresh(message)
            return message
        except Exception as e:
            logger.error(f"Error creating message: {e}")
            raise e

    async def get_by_chat_id(self, chat_id: uuid.UUID) -> List[MessageDB]:
        try:
            result = await self.db.execute(
                select(MessageDB)
                .where(MessageDB.chat_id == chat_id)
                .order_by(MessageDB.created_at)
            )
            messages = result.scalars().all()
            return [
                MessageDB(
                    id=message.id,
                    chat_id=message.chat_id,
                    role=message.role,
                    content=message.content,
                    created_at=message.created_at,
                )
                for message in messages
            ]
        except Exception as e:
            logger.error(f"Error getting messages by chat id: {e}")
            raise e

    async def count_by_chat(self, chat_id: uuid.UUID) -> int:
        try:
            result = await self.db.execute(
                select(func.count(MessageDB.id)).where(MessageDB.chat_id == chat_id)
            )
            sc = result.scalar()
            if sc is None:
                return 0
            return sc
        except Exception as e:
            logger.error(f"Error counting messages by chat id: {e}")
            raise e
