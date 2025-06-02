from pydantic import BaseModel, Field
from datetime import datetime

class Workspace(BaseModel):
    id: str = Field(..., description="Workspace ID")
    name: str = Field(..., description="Workspace name")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CreateWorkspacePayload(BaseModel):
    name: str = Field(..., description="Workspace name")


class WorkspaceDto(BaseModel):
    """Response model for workspace operations"""
    id: str
    name: str
    created_at: datetime
    updated_at: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

