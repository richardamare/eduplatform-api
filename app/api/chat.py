from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.services.chat_service import chat_service
from app.models.message import MessageDto
from app.models.chat import ChatDto
from app.database import get_db

router = APIRouter(prefix="/chats", tags=["chats"])


class ChatMessageRequest(BaseModel):
    message: str
    chat_id: str = Field(..., alias="chatId")


class CreateChatRequest(BaseModel):
    workspace_id: str = Field(..., alias="workspaceId")


@router.post("/stream")
async def chat_stream(payload: ChatMessageRequest):
    """Streaming chat endpoint with RAG context"""

    try:
        stream = await chat_service.stream(payload.message, payload.chat_id)

        return StreamingResponse(
            stream,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{chat_id}")
async def get_chat(chat_id: str, db: AsyncSession = Depends(get_db)) -> ChatDto:
    """Get a specific chat"""

    try:
        chat = await chat_service.get_by_id(chat_id)
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        return chat
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{chat_id}/messages")
async def get_chat_messages(chat_id: str) -> List[MessageDto]:
    """Get all messages for a specific chat"""

    try:
        chat = await chat_service.get_by_id(chat_id)
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")

        messages = await chat_service.get_messages_by_chat_id(chat_id)
        return messages
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=ChatDto)
async def create_chat(request: CreateChatRequest) -> ChatDto:
    """Create a new chat"""

    try:
        chat = await chat_service.create_chat("New name", request.workspace_id)
        return chat
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
