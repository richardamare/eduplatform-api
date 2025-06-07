from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class VectorSearchResult(BaseModel):
    vector_id: int
    file_path: str
    content_text: str
    similarity: float


class SourceFileDto(BaseModel):
    id: int
    file_path: str
    file_name: str
    content_type: str
    workspace_id: str
    file_size: Optional[int] = None
    created_at: datetime
    chunks_count: Optional[int] = None  # Can be populated separately
