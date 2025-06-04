from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from pydantic import BaseModel

from app.database import get_db
from app.services.rag_service import RAGService
from app.models.rag import VectorSearchResult
from app.services.azure_blob_service import get_azure_blob_service, BlobUploadUrl
from app.services.document_processor import DocumentProcessor
import os

router = APIRouter(prefix="/rag", tags=["RAG"])

class SimilaritySearchRequest(BaseModel):
    query: str
    limit: int = 5
    min_similarity: float = 0.0

class GenerateUploadUrlRequest(BaseModel):
    fileName: str
    fileSize: int
    mimeType: str

class ConfirmUploadRequest(BaseModel):
    blobName: str
    fileName: str
    replaceExisting: bool = False

class ProcessedDocumentResponse(BaseModel):
    id: str
    name: str
    blobName: str
    workspace_id: str
    chunks_count: int
    status: str
    processed_at: str

@router.post("/search", response_model=List[VectorSearchResult])
async def search_documents(
    request: SimilaritySearchRequest,
    db: AsyncSession = Depends(get_db)
):
    """Search for similar documents using vector similarity"""
    try:
        rag_service = RAGService()
        results = await rag_service.search_similar_vectors(
            db=db,
            query_text=request.query,
            limit=request.limit,
            min_similarity=request.min_similarity
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/documents")
async def list_documents(db: AsyncSession = Depends(get_db)):
    """List all available documents"""
    try:
        rag_service = RAGService()
        files = await rag_service.get_all_source_files(db)
        return [{"id": file_id, "file_path": file_path} for file_id, file_path in files]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")

@router.post("/workspaces/{workspace_id}/documents/upload-url", response_model=BlobUploadUrl)
async def generate_upload_url(
    workspace_id: str,
    request: GenerateUploadUrlRequest
):
    """Generate a SAS URL for direct client-side upload to Azure Blob Storage"""
    try:
        azure_blob_service = get_azure_blob_service()
        blob_name = azure_blob_service.generate_unique_blob_name(request.fileName, workspace_id)
        
        upload_url_info = azure_blob_service.create_blob_upload_url(
            blob_name=blob_name,
            content_type=request.mimeType,
            expiry_minutes=180  # 3 hours
        )
        
        return upload_url_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate upload URL: {str(e)}")

@router.post("/workspaces/{workspace_id}/documents/confirm-upload", response_model=ProcessedDocumentResponse)
async def confirm_upload_and_process(
    workspace_id: str,
    request: ConfirmUploadRequest,
    db: AsyncSession = Depends(get_db)
):
    """Confirm upload and immediately process document for RAG"""
    try:
        # Initialize services
        rag_service = RAGService()
        azure_blob_service = get_azure_blob_service()
        document_processor = DocumentProcessor()
        
        # Check if document already exists
        file_exists = await rag_service.document_exists(db, request.blobName)
        
        if file_exists and not request.replaceExisting:
            raise HTTPException(
                status_code=409, 
                detail=f"Document already exists: {request.fileName}. Set replaceExisting=true to replace."
            )
        
        # Download file from blob storage
        from app.config import settings
        blob_client = azure_blob_service.blob_service_client.get_blob_client(
            container=settings.azure_storage_container_name,
            blob=request.blobName
        )
        
        file_content = blob_client.download_blob().readall()
        
        # Process document to extract text chunks
        text_chunks = document_processor.process_file(file_content, request.fileName)
        
        # Insert document with chunks into RAG system
        await rag_service.insert_document_with_chunks(
            db=db,
            file_path=request.blobName,
            text_chunks=text_chunks,
            replace_existing=request.replaceExisting
        )
        
        # Return processed document info
        from datetime import datetime
        return ProcessedDocumentResponse(
            id=request.blobName,
            name=request.fileName,
            blobName=request.blobName,
            workspace_id=workspace_id,
            chunks_count=len(text_chunks),
            status="completed",
            processed_at=datetime.utcnow().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@router.get("/workspaces/{workspace_id}/documents")
async def list_workspace_documents(workspace_id: str, db: AsyncSession = Depends(get_db)):
    """List documents within a specific workspace"""
    try:
        rag_service = RAGService()
        files = await rag_service.get_all_source_files(db)
        # Filter for workspace
        workspace_files = [
            {"id": file_id, "file_path": file_path} 
            for file_id, file_path in files 
            if file_path.startswith(f"{workspace_id}/")
        ]
        return workspace_files
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list workspace documents: {str(e)}")

@router.post("/workspaces/{workspace_id}/search", response_model=List[VectorSearchResult])
async def search_workspace_documents(
    workspace_id: str,
    request: SimilaritySearchRequest,
    db: AsyncSession = Depends(get_db)
):
    """Search for similar documents within a specific workspace"""
    try:
        rag_service = RAGService()
        # Search all documents first
        results = await rag_service.search_similar_vectors(
            db=db,
            query_text=request.query,
            limit=request.limit * 3,  # Get more results to filter
            min_similarity=request.min_similarity
        )
        
        # Filter for workspace and limit results
        workspace_results = [
            result for result in results 
            if result.file_path.startswith(f"{workspace_id}/")
        ][:request.limit]
        
        return workspace_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workspace search failed: {str(e)}")

@router.delete("/workspaces/{workspace_id}/documents/{document_id}")
async def delete_document(
    workspace_id: str,
    document_id: str,
    delete_blob: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """Delete a document from RAG system and optionally from blob storage"""
    try:
        rag_service = RAGService()
        
        # Verify document belongs to workspace
        if not document_id.startswith(f"{workspace_id}/"):
            raise HTTPException(status_code=403, detail="Document does not belong to this workspace")
        
        # Delete from RAG system
        success = await rag_service.delete_source_file(db, document_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Optionally delete from blob storage
        if delete_blob:
            azure_blob_service = get_azure_blob_service()
            blob_deleted = azure_blob_service.delete_blob(document_id)
            if not blob_deleted:
                # Log warning but don't fail the request
                import logging
                logging.warning(f"Failed to delete blob {document_id}, but RAG data was removed")
        
        return {"message": f"Document {document_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}") 