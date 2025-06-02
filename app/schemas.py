from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid


class DocumentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    source: Optional[str] = Field(None, max_length=500)
    metadata: Optional[Dict[str, Any]] = None


class DocumentResponse(BaseModel):
    id: uuid.UUID
    title: str
    content: str
    source: Optional[str]
    metadata: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    is_active: bool

    class Config:
        from_attributes = True


class ChatMessageCreate(BaseModel):
    content: str = Field(..., min_length=1)


class ChatMessageResponse(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    metadata: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ChatSessionCreate(BaseModel):
    user_id: Optional[str] = None
    title: Optional[str] = None


class ChatSessionResponse(BaseModel):
    id: uuid.UUID
    user_id: Optional[str]
    title: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    is_active: bool
    messages: List[ChatMessageResponse] = []

    class Config:
        from_attributes = True


class ChatResponse(BaseModel):
    message: str
    sources: List[Dict[str, Any]] = []
    session_id: uuid.UUID


class SearchQuery(BaseModel):
    query: str = Field(..., min_length=1)
    limit: int = Field(default=5, ge=1, le=20)


class SearchResult(BaseModel):
    content: str
    source: Optional[str]
    score: float
    document_title: str 