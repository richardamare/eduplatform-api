from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.services.azure_blob_service import (
    azure_blob_service,
    CreateBlobUploadUrlResult,
)
from app.services.rag_service import rag_service
from app.services.document_processor import document_processor

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
    blob_name: str
    file_name: str
    replace_existing: bool = False
    mime_type: str


class ProcessedDocumentResponse(BaseModel):
    id: str
    name: str
    blobName: str
    workspace_id: str
    chunks_count: int
    status: str
    processed_at: str


@router.post(
    "/workspaces/{workspace_id}/documents/upload-url",
    response_model=CreateBlobUploadUrlResult,
)
async def generate_upload_url(workspace_id: str, request: GenerateUploadUrlRequest):
    """Generate a SAS URL for direct client-side upload to Azure Blob Storage"""
    try:
        blob_name = azure_blob_service.generate_unique_blob_name(
            filename=request.fileName, workspace_id=workspace_id
        )

        return azure_blob_service.create_blob_upload_url(
            blob_name=blob_name,
            content_type=request.mimeType,
            expiry_minutes=180,  # 3 hours
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/workspaces/{workspace_id}/documents/confirm-upload",
    response_model=ProcessedDocumentResponse,
)
async def confirm_upload_and_process(
    workspace_id: str, request: ConfirmUploadRequest, db: AsyncSession = Depends(get_db)
):
    """Confirm upload and immediately process document for RAG"""
    try:
        # Check if document already exists
        file_exists = await rag_service.document_exists(request.blob_name)

        if file_exists and not request.replace_existing:
            raise HTTPException(
                status_code=409,
                detail=f"Document already exists: {request.file_name}. Set replace_existing=true to replace.",
            )

        blob_client = azure_blob_service._get_blob_client(request.blob_name)

        file_content = blob_client.download_blob().readall()

        # Process document to extract text chunks
        text_chunks = document_processor.process_file(file_content, request.file_name)

        # Insert document with chunks into RAG system
        await rag_service.insert_document_with_chunks(
            file_path=request.blob_name,
            file_name=request.file_name,
            content_type=request.mime_type,
            workspace_id=workspace_id,
            text_chunks=text_chunks,
            replace_existing=request.replace_existing,
        )

        return ProcessedDocumentResponse(
            id=request.blob_name,
            name=request.file_name,
            blob_name=request.blob_name,
            workspace_id=workspace_id,
            chunks_count=len(text_chunks),
            status="completed",
            processed_at=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
