from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class Message(BaseModel):
    id: str = Field(..., description="Message ID")
    role: MessageRole = Field(..., description="Message role (user or assistant)")
    content: str = Field(..., description="Message content")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CreateMessagePayload(BaseModel):
    role: MessageRole = Field(..., description="Message role (user or assistant)")
    content: str = Field(..., description="Message content")


class MessageDto(BaseModel):
    """Response model for message operations"""
    id: str
    role: MessageRole
    content: str
    created_at: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        } 