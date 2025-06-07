from fastapi import (
    APIRouter,
    HTTPException,
)
from pydantic import BaseModel, Field
import os

from app.services.azure_blob_service import (
    CreateBlobUploadUrlResult,
    azure_blob_service,
)
from app.services.rag_service import rag_service
from app.services.document_processor import document_processor
from app.models.rag import SourceFileDto

router = APIRouter(prefix="/attachments", tags=["attachments"])


class GenerateUploadUrlRequest(BaseModel):
    file_name: str = Field(..., alias="fileName")
    file_size: int = Field(..., alias="fileSize")
    mime_type: str = Field(..., alias="mimeType")


@router.post(
    "/{workspace_id}/generate-upload-url", response_model=CreateBlobUploadUrlResult
)
async def generate_upload_url(workspace_id: str, request: GenerateUploadUrlRequest):
    """Generate a SAS URL for direct client-side upload to Azure Blob Storage"""
    try:
        blob_name = azure_blob_service.generate_unique_blob_name(
            request.file_name, workspace_id
        )

        return azure_blob_service.create_blob_upload_url(
            blob_name=blob_name,
            content_type=request.mime_type,
            expiry_minutes=180,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ConfirmUploadRequest(BaseModel):
    blob_name: str = Field(..., alias="blobName")
    file_name: str = Field(..., alias="fileName")


@router.post("/{workspace_id}/confirm-upload", response_model=SourceFileDto)
async def confirm_blob_upload(workspace_id: str, request: ConfirmUploadRequest):
    """Confirm that a file was uploaded via SAS URL and process with RAG"""

    try:
        await rag_service.ensure_database_setup()

        file_content = azure_blob_service.get_blob_content(request.blob_name)

        # Process document to extract text chunks
        text_chunks = document_processor.process_file(file_content, request.file_name)

        # Get file extension and content type
        file_extension = os.path.splitext(request.file_name)[1].lower()
        content_type = document_processor.get_content_type_from_extension(
            file_extension
        )

        # Insert document with chunks into RAG system
        source_file_dto = await rag_service.insert_document_with_chunks(
            file_path=request.blob_name,
            file_name=request.file_name,
            content_type=content_type,
            workspace_id=workspace_id,
            text_chunks=text_chunks,
            file_size=len(file_content),
            replace_existing=True,
        )

        return source_file_dto

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
