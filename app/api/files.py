from fastapi import (
    APIRouter,
    BackgroundTasks,
    HTTPException,
)
from pydantic import BaseModel, Field

from app.file.model import GenerateUploadUrlDto, SourceFileDto
from app.file.service import file_service

router = APIRouter(prefix="/files", tags=["files"])


class GenerateUploadUrlRequest(BaseModel):
    file_name: str = Field(..., alias="fileName")
    file_size: int = Field(..., alias="fileSize")
    mime_type: str = Field(..., alias="mimeType")


@router.post("/{workspace_id}/upload-url", response_model=GenerateUploadUrlDto)
async def generate_upload_url(workspace_id: str, request: GenerateUploadUrlRequest):
    """Generate a SAS URL for direct client-side upload to Azure Blob Storage"""
    try:
        return await file_service.generate_upload_url(
            file_name=request.file_name,
            content_type=request.mime_type,
            workspace_id=workspace_id,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ConfirmUploadRequest(BaseModel):
    blob_name: str = Field(..., alias="blobName")
    file_name: str = Field(..., alias="fileName")


@router.post("/{workspace_id}/confirm-upload", response_model=SourceFileDto)
async def confirm_blob_upload(
    workspace_id: str, request: ConfirmUploadRequest, background_tasks: BackgroundTasks
):
    """Confirm that a file was uploaded via SAS URL and process with RAG"""

    try:
        background_tasks.add_task(
            file_service.process_file,
            request.blob_name,
            request.file_name,
            workspace_id,
            replace_existing=True,
        )

        return SourceFileDto(
            id=request.blob_name,
            name=request.file_name,
            blob_name=request.blob_name,
            workspace_id=workspace_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
