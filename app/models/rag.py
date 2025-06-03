from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from enum import Enum

class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class DocumentRecord(BaseModel):
    id: Optional[int] = None
    file_path: str
    content: str
    vector: Optional[List[float]] = None

class VectorSearchResult(BaseModel):
    id: int
    file_path: str
    snippet: str
    similarity: float

class VectorInsertRequest(BaseModel):
    file_path: str
    snippets: List[str]  # Text chunks to vectorize
    
class SimilaritySearchRequest(BaseModel):
    query: str
    limit: int = 5
    min_similarity: float = 0.0 

class ProcessingJob(BaseModel):
    job_id: str
    file_name: str
    status: ProcessingStatus
    message: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    chunks_created: Optional[int] = None
    error_details: Optional[str] = None

class UploadResponse(BaseModel):
    job_id: str
    file_name: str
    status: ProcessingStatus
    message: str
    estimated_processing_time: str 