from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid
from app.database import get_db
from app.schemas import DocumentCreate, DocumentResponse, SearchQuery, SearchResult
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    document: DocumentCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new document with vector embeddings"""
    try:
        new_document = await DocumentService.create_document(db, document)
        return new_document
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating document: {str(e)}"
        )


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    title: str = None,
    source: str = None,
    db: AsyncSession = Depends(get_db)
):
    """Upload and create a document from file"""
    try:
        content = await file.read()
        content_str = content.decode('utf-8')
        
        document_data = DocumentCreate(
            title=title or file.filename,
            content=content_str,
            source=source or file.filename
        )
        
        new_document = await DocumentService.create_document(db, document_data)
        return new_document
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a text file"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading document: {str(e)}"
        )


@router.get("/", response_model=List[DocumentResponse])
async def get_documents(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Get all documents"""
    documents = await DocumentService.get_documents(db, skip, limit)
    return documents


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific document"""
    document = await DocumentService.get_document(db, str(document_id))
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a document"""
    success = await DocumentService.delete_document(db, str(document_id))
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )


@router.post("/search", response_model=List[SearchResult])
async def search_documents(
    search_query: SearchQuery,
    db: AsyncSession = Depends(get_db)
):
    """Search documents using vector similarity"""
    try:
        results = await DocumentService.search_similar_chunks(
            db, search_query.query, search_query.limit
        )
        return results
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching documents: {str(e)}"
        ) 