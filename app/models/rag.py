from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

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