from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import tempfile
import os
from pathlib import Path

from app.database import get_db
from app.services.rag_service import RAGService
from app.services.document_processor import DocumentProcessor
from app.models.rag import (
    DocumentRecord, 
    VectorSearchResult, 
    VectorInsertRequest, 
    SimilaritySearchRequest
)

router = APIRouter(prefix="/rag", tags=["RAG"])

# Initialize services
rag_service = RAGService()
doc_processor = DocumentProcessor()

@router.post("/setup")
async def setup_rag_database(db: AsyncSession = Depends(get_db)):
    """Initialize RAG database setup (pgvector extension and functions)."""
    try:
        await rag_service.ensure_database_setup(db)
        return {"message": "RAG database setup completed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Setup failed: {str(e)}")

@router.post("/upload-file")
async def upload_and_vectorize_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Upload a file, process it, and store vector embeddings."""
    try:
        # Read file content
        file_content = await file.read()
        
        # Process file and extract text chunks
        chunks = doc_processor.process_file(file_content, file.filename)
        
        if not chunks:
            raise HTTPException(status_code=400, detail="No text content could be extracted from file")
        
        # Store chunks with embeddings
        await rag_service.insert_document_with_chunks(
            db=db,
            file_path=file.filename,
            text_chunks=chunks
        )
        
        return {
            "message": f"File {file.filename} processed successfully",
            "chunks_created": len(chunks),
            "file_path": file.filename
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File processing failed: {str(e)}")

@router.post("/insert-text")
async def insert_text_record(
    request: VectorInsertRequest,
    db: AsyncSession = Depends(get_db)
):
    """Insert text snippets directly with embeddings."""
    try:
        await rag_service.insert_document_with_chunks(
            db=db,
            file_path=request.file_path,
            text_chunks=request.snippets
        )
        
        return {
            "message": f"Inserted {len(request.snippets)} text chunks",
            "file_path": request.file_path
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Text insertion failed: {str(e)}")

@router.post("/search", response_model=List[VectorSearchResult])
async def search_similar_content(
    request: SimilaritySearchRequest,
    db: AsyncSession = Depends(get_db)
):
    """Search for similar content using vector similarity."""
    try:
        results = await rag_service.search_similar_vectors(
            db=db,
            query_text=request.query,
            limit=request.limit,
            min_similarity=request.min_similarity
        )
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/search/{query}")
async def search_similar_content_get(
    query: str,
    limit: int = 5,
    min_similarity: float = 0.0,
    db: AsyncSession = Depends(get_db)
):
    """Search for similar content using GET request."""
    try:
        results = await rag_service.search_similar_vectors(
            db=db,
            query_text=query,
            limit=limit,
            min_similarity=min_similarity
        )
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/document/{vector_id}")
async def get_document_by_id(
    vector_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve a document record by vector ID."""
    try:
        record = await rag_service.get_document_record_by_id(db, vector_id)
        
        if not record:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return record
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {str(e)}")

@router.get("/files")
async def list_source_files(db: AsyncSession = Depends(get_db)):
    """List all source files."""
    try:
        files = await rag_service.get_all_source_files(db)
        return [{"id": file_id, "file_path": file_path} for file_id, file_path in files]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve files: {str(e)}")

@router.get("/vectors")
async def list_all_vectors(db: AsyncSession = Depends(get_db)):
    """List all vectors (for debugging)."""
    try:
        vectors = await rag_service.get_all_vectors(db)
        
        return [
            {
                "id": vector_id,
                "source_file_id": source_file_id,
                "snippet": snippet[:100] + "..." if len(snippet) > 100 else snippet,
                "vector_dimensions": len(vector_data) if vector_data else 0
            }
            for vector_id, source_file_id, snippet, vector_data in vectors
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve vectors: {str(e)}")

@router.delete("/file/{file_path:path}")
async def delete_source_file(
    file_path: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a source file and all its vectors."""
    try:
        deleted = await rag_service.delete_source_file(db, file_path)
        
        if not deleted:
            raise HTTPException(status_code=404, detail="File not found")
        
        return {"message": f"File {file_path} and all associated vectors deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deletion failed: {str(e)}") 