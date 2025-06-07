from pydantic import BaseModel
from datetime import datetime
from enum import Enum


class ChatDto(BaseModel):
    """Response model for chat operations"""

    id: str
    name: str
    workspace_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class MessageDto(BaseModel):
    """Response model for message operations"""

    id: str
    role: MessageRole
    content: str
    created_at: datetime

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
