from pydantic import BaseModel
from datetime import datetime


class WorkspaceDto(BaseModel):
    """Response model for workspace operations"""

    id: str
    name: str
    created_at: datetime
    updated_at: datetime

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
