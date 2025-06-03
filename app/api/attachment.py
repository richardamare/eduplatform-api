from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.database import get_db
from app.models.attachment import CreateAttachmentPayload, AttachmentDto, AttachmentSearchResult
from app.services.repositories import AttachmentRepository

router = APIRouter(prefix="/attachments", tags=["attachments"])

@router.post("/", response_model=AttachmentDto)
async def create_attachment(
    payload: CreateAttachmentPayload,
    db: AsyncSession = Depends(get_db)
):
    """Create a new attachment"""
    repo = AttachmentRepository(db)
    return await repo.create(payload)

@router.get("/{attachment_id}", response_model=AttachmentDto)
async def get_attachment(
    attachment_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get attachment by ID"""
    repo = AttachmentRepository(db)
    attachment = await repo.get_by_id(attachment_id)
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    return attachment

@router.get("/workspace/{workspace_id}", response_model=List[AttachmentDto])
async def get_workspace_attachments(
    workspace_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all attachments for a workspace"""
    repo = AttachmentRepository(db)
    return await repo.get_by_workspace(workspace_id)

@router.put("/{attachment_id}/vector")
async def update_attachment_vector(
    attachment_id: str,
    vector: List[float],
    db: AsyncSession = Depends(get_db)
):
    """Update attachment's vector content"""
    repo = AttachmentRepository(db)
    success = await repo.update_vector(attachment_id, vector)
    if not success:
        raise HTTPException(status_code=404, detail="Attachment not found")
    return {"message": "Vector updated successfully"}

@router.post("/search", response_model=List[AttachmentSearchResult])
async def search_similar_attachments(
    query_vector: List[float],
    workspace_id: str,
    limit: int = Query(10, le=50),
    similarity_threshold: float = Query(0.7, le=1.0, ge=0.0),
    db: AsyncSession = Depends(get_db)
):
    """Search for similar attachments using vector similarity"""
    repo = AttachmentRepository(db)
    return await repo.vector_similarity_search(
        query_vector=query_vector,
        workspace_id=workspace_id,
        limit=limit,
        similarity_threshold=similarity_threshold
    )

@router.delete("/{attachment_id}")
async def delete_attachment(
    attachment_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete an attachment"""
    repo = AttachmentRepository(db)
    success = await repo.delete(attachment_id)
    if not success:
        raise HTTPException(status_code=404, detail="Attachment not found")
    return {"message": "Attachment deleted successfully"} 