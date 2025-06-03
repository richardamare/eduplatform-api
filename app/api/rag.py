from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import tempfile
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

from app.database import get_db
from app.services.rag_service import RAGService
from app.services.document_processor import DocumentProcessor
from app.models.rag import (
    DocumentRecord, 
    VectorSearchResult, 
    VectorInsertRequest, 
    SimilaritySearchRequest,
    UploadResponse,
    ProcessingJob,
    ProcessingStatus
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

@router.post("/upload-file", response_model=UploadResponse)
async def upload_and_vectorize_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    replace_existing: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """Upload a file and process it in the background."""
    try:
        logger.info(f"Starting upload for file: {file.filename}")
        
        # Read file content
        file_content = await file.read()
        logger.info(f"File content read: {len(file_content)} bytes")
        
        if len(file_content) == 0:
            raise HTTPException(status_code=400, detail="Empty file uploaded")
        
        # Quick estimate processing time based on file type and size
        file_size_mb = len(file_content) / (1024 * 1024)
        if file.filename.lower().endswith('.pdf'):
            if file_size_mb > 10:
                estimated_time = "5-15 minutes for large PDFs"
            else:
                estimated_time = "2-5 minutes for PDFs"
        elif file.filename.lower().endswith(('.docx', '.doc')):
            estimated_time = "1-3 minutes for Word documents"
        else:
            estimated_time = "30 seconds - 2 minutes"
        
        # Create processing job
        job = rag_service.create_processing_job(file.filename)
        logger.info(f"Created processing job: {job.job_id}")
        
        # Start background processing immediately
        background_tasks.add_task(
            rag_service.process_document_background,
            job.job_id,
            file_content,
            file.filename,
            db,
            replace_existing
        )
        logger.info(f"Background task started for job: {job.job_id}")
        
        # Return immediately
        return UploadResponse(
            job_id=job.job_id,
            file_name=file.filename,
            status=ProcessingStatus.PENDING,
            message="File uploaded successfully. Processing started in background.",
            estimated_processing_time=estimated_time
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")

@router.get("/job/{job_id}", response_model=ProcessingJob)
async def get_processing_status(job_id: str):
    """Get the status of a background processing job."""
    job = rag_service.get_processing_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job

@router.get("/jobs")
async def list_processing_jobs():
    """List all processing jobs (for debugging)."""
    return {
        "jobs": list(rag_service.processing_jobs.values()),
        "total_jobs": len(rag_service.processing_jobs)
    }

@router.post("/upload-file-sync")
async def upload_and_vectorize_file_sync(
    file: UploadFile = File(...),
    replace_existing: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """Upload a file and process it synchronously (original behavior)."""
    try:
        # Read file content
        file_content = await file.read()
        
        # Process file and extract text chunks
        chunks = doc_processor.process_file(file_content, file.filename)
        
        if not chunks:
            raise HTTPException(status_code=400, detail="No text content could be extracted from file")
        
        # Check if document already exists
        existing_count = await rag_service.get_document_vector_count(db, file.filename)
        
        if existing_count > 0 and not replace_existing:
            return {
                "message": f"File {file.filename} already exists with {existing_count} vectors",
                "action": "skipped",
                "file_path": file.filename,
                "existing_vector_count": existing_count,
                "suggestion": "Use replace_existing=true to overwrite"
            }
        
        # Use upsert method for better handling
        if replace_existing:
            result = await rag_service.upsert_document_with_chunks(
                db=db,
                file_path=file.filename,
                text_chunks=chunks
            )
        else:
            await rag_service.insert_document_with_chunks(
                db=db,
                file_path=file.filename,
                text_chunks=chunks
            )
            result = {
                "action": "created",
                "file_path": file.filename,
                "chunks_count": len(chunks)
            }
        
        return {
            "message": f"File {file.filename} processed successfully",
            **result
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File processing failed: {str(e)}")

@router.post("/upsert-file")
async def upsert_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Upload a file and replace if it already exists (background processing)."""
    return await upload_and_vectorize_file(
        background_tasks=background_tasks,
        file=file,
        replace_existing=True,
        db=db
    )

@router.get("/document-info/{file_path:path}")
async def get_document_info(
    file_path: str,
    db: AsyncSession = Depends(get_db)
):
    """Get information about a document including vector count."""
    try:
        exists = await rag_service.document_exists(db, file_path)
        if not exists:
            raise HTTPException(status_code=404, detail="Document not found")
        
        vector_count = await rag_service.get_document_vector_count(db, file_path)
        
        return {
            "file_path": file_path,
            "exists": True,
            "vector_count": vector_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get document info: {str(e)}")

@router.post("/insert-text")
async def insert_text_record(
    request: VectorInsertRequest,
    replace_existing: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """Insert text snippets directly with embeddings."""
    try:
        if replace_existing:
            result = await rag_service.upsert_document_with_chunks(
                db=db,
                file_path=request.file_path,
                text_chunks=request.snippets
            )
        else:
            await rag_service.insert_document_with_chunks(
                db=db,
                file_path=request.file_path,
                text_chunks=request.snippets
            )
            result = {
                "action": "created",
                "file_path": request.file_path,
                "chunks_count": len(request.snippets)
            }
        
        return {
            "message": f"Inserted {len(request.snippets)} text chunks",
            **result
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