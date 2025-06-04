from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import os

from app.database import get_db
from app.services.azure_blob_service import get_azure_blob_service, BlobUploadUrl
from app.services.polling_service import polling_service, PollingJob
from app.services.rag_service import RAGService
from app.services.document_processor import DocumentProcessor
from app.models.rag import SourceFileDto
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/attachments", tags=["attachments"])

# Legacy endpoints for compatibility - consider deprecating
@router.get("/workspace/{workspace_id}", response_model=List[SourceFileDto])
async def get_workspace_attachments(
    workspace_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all files for a workspace (now using RAG source_files table)"""
    rag_service = RAGService()
    return await rag_service.get_workspace_source_files(db, workspace_id)

@router.delete("/{file_path:path}")
async def delete_attachment(
    file_path: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a file (now using RAG source_files table)"""
    rag_service = RAGService()
    success = await rag_service.delete_source_file(db, file_path)
    if not success:
        raise HTTPException(status_code=404, detail="File not found")
    return {"message": "File deleted successfully"}

# Removed legacy create_attachment and get_attachment endpoints

class GenerateUploadUrlRequest(BaseModel):
    fileName: str
    fileSize: int
    mimeType: str

@router.post("/{workspace_id}/generate-upload-url", response_model=BlobUploadUrl)
async def generate_upload_url(
        workspace_id: str,
    request: GenerateUploadUrlRequest
):
    """Generate a SAS URL for direct client-side upload to Azure Blob Storage"""
    try:
        print('request', request)
        # Get Azure Blob Service
        azure_blob_service = get_azure_blob_service()

        # Generate unique blob name
        blob_name = azure_blob_service.generate_unique_blob_name(request.fileName, workspace_id)

        # Generate SAS URL
        upload_url_info = azure_blob_service.create_blob_upload_url(
            blob_name=blob_name,
            content_type=request.mimeType,
            expiry_minutes=3 * 60 # 3 hours
        )

        print('upload_url_info', upload_url_info)

        return upload_url_info

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate upload URL: {str(e)}")


class ConfirmUploadRequest(BaseModel):
    blob_name: str
    filename: str

@router.post("/{workspace_id}/confirm-upload", response_model=SourceFileDto)
async def confirm_blob_upload(
    workspace_id: str,
    request: ConfirmUploadRequest,
    db: AsyncSession = Depends(get_db)
):
    """Confirm that a file was uploaded via SAS URL and process with RAG"""
    try:
        logger.info(f"Starting file confirmation and RAG processing for: {request.filename}")
        
        # Initialize services
        rag_service = RAGService()
        azure_blob_service = get_azure_blob_service()
        document_processor = DocumentProcessor()
        
        # Ensure RAG database setup
        await rag_service.ensure_database_setup(db)
        
        # Download file content from blob storage
        file_content = azure_blob_service.get_blob_content(request.blob_name)
        
        # Process document to extract text chunks
        text_chunks = document_processor.process_file(file_content, request.filename)
        
        # Get file extension and content type
        file_extension = os.path.splitext(request.filename)[1].lower()
        content_type = _get_content_type_from_extension(file_extension)
        
        # Insert document with chunks into RAG system
        source_file_dto = await rag_service.insert_document_with_chunks(
            db=db,
            file_path=request.blob_name,
            file_name=request.filename,
            content_type=content_type,
            workspace_id=workspace_id,
            text_chunks=text_chunks,
            file_size=len(file_content),
            replace_existing=True
        )
        
        logger.info(f"RAG processing completed for {request.filename}: {len(text_chunks)} chunks created")
        
        return source_file_dto

    except Exception as e:
        logger.error(f"Failed to confirm upload and process file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to confirm upload: {str(e)}")

def _get_content_type_from_extension(extension: str) -> str:
    """Map file extension to content type"""
    content_types = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".doc": "application/msword",
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".py": "text/x-python",
        ".js": "text/javascript",
        ".html": "text/html",
        ".css": "text/css",
        ".json": "application/json",
        ".xml": "application/xml"
    }
    return content_types.get(extension, "application/octet-stream")

@router.get("/{file_path:path}/download-url")
async def get_download_url(
    file_path: str,
    expiry_minutes: int = 60,
    db: AsyncSession = Depends(get_db)
):
    """Get a download URL for a file"""
    try:
        # Check if file exists in RAG system
        rag_service = RAGService()
        file_exists = await rag_service.document_exists(db, file_path)
        
        if not file_exists:
            raise HTTPException(status_code=404, detail="File not found")

        # Get Azure Blob Service
        azure_blob_service = get_azure_blob_service()

        # Generate download URL
        download_url = azure_blob_service.generate_download_sas_url(
            blob_name=file_path,
            expiry_minutes=expiry_minutes
        )

        # Extract filename from path
        filename = file_path.split('/')[-1] if '/' in file_path else file_path

        return {
            "download_url": download_url,
            "filename": filename,
            "expiry_minutes": expiry_minutes
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get download URL: {str(e)}")