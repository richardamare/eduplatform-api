from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

class Attachment(BaseModel):
    id: str = Field(..., description="Attachment ID")
    name: str = Field(..., description="Attachment name")
    type: str = Field(..., description="File type/extension")
    azure_blob_path: str = Field(..., description="Azure blob storage path")
    workspace_id: str = Field(..., description="Workspace ID")
    content_vector: Optional[List[float]] = Field(None, description="Vectorized content")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class CreateAttachmentPayload(BaseModel):
    name: str = Field(..., description="Attachment name")
    type: str = Field(..., description="File type/extension")
    azure_blob_path: str = Field(..., description="Azure blob storage path")
    workspace_id: str = Field(..., description="Workspace ID")
    content_vector: Optional[List[float]] = Field(None, description="Vectorized content")

class AttachmentDto(BaseModel):
    """Response model for attachment operations"""
    id: str
    name: str
    type: str
    azure_blob_path: str
    workspace_id: str
    content_vector: Optional[List[float]]
    created_at: datetime
    updated_at: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class AttachmentSearchResult(BaseModel):
    """Result model for vector similarity search"""
    attachment: AttachmentDto
    similarity_score: float = Field(..., description="Cosine similarity score") 