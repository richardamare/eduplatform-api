from pydantic import BaseModel, Field
from datetime import datetime

class Chat(BaseModel):
    id: str = Field(..., description="Chat ID")
    name: str = Field(..., description="Chat name")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ChatDto(BaseModel):
    """Response model for chat operations"""
    id: str
    name: str
    created_at: datetime
    updated_at: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        } 