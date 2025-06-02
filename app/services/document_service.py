from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import List, Dict, Any, Optional
import json
from app.models import Document, DocumentChunk
from app.schemas import DocumentCreate, SearchResult
from app.services.azure_openai import azure_openai
from app.config import settings


class DocumentService:
    
    @staticmethod
    def chunk_text(text: str, chunk_size: int = None, overlap: int = None) -> List[str]:
        """Split text into chunks with overlap"""
        chunk_size = chunk_size or settings.chunk_size
        overlap = overlap or settings.chunk_overlap
        
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            
            # Try to end at a sentence boundary
            if end < len(text):
                last_period = chunk.rfind('.')
                last_newline = chunk.rfind('\n')
                boundary = max(last_period, last_newline)
                
                if boundary > start + chunk_size * 0.5:  # Don't make chunks too small
                    end = start + boundary + 1
                    chunk = text[start:end]
            
            chunks.append(chunk.strip())
            start = end - overlap
            
            if start >= len(text):
                break
        
        return chunks
    
    @staticmethod
    async def create_document(db: AsyncSession, document_data: DocumentCreate) -> Document:
        """Create a new document with embeddings"""
        # Create document
        document = Document(
            title=document_data.title,
            content=document_data.content,
            source=document_data.source,
            metadata=json.dumps(document_data.metadata) if document_data.metadata else None
        )
        
        db.add(document)
        await db.flush()  # Get the document ID
        
        # Chunk the content
        chunks = DocumentService.chunk_text(document_data.content)
        
        # Get embeddings for all chunks
        embeddings = await azure_openai.get_embeddings(chunks)
        
        # Create document chunks with embeddings
        for i, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
            chunk = DocumentChunk(
                document_id=document.id,
                content=chunk_text,
                chunk_index=i,
                embedding=embedding
            )
            db.add(chunk)
        
        await db.commit()
        await db.refresh(document)
        return document
    
    @staticmethod
    async def search_similar_chunks(
        db: AsyncSession, 
        query: str, 
        limit: int = 5
    ) -> List[SearchResult]:
        """Search for similar document chunks using vector similarity"""
        # Get query embedding
        query_embedding = await azure_openai.get_embedding(query)
        
        # Vector similarity search using cosine distance
        sql = text("""
            SELECT 
                dc.content,
                d.title as document_title,
                d.source,
                1 - (dc.embedding <=> :query_embedding) as similarity_score
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.id
            WHERE d.is_active = true
            ORDER BY dc.embedding <=> :query_embedding
            LIMIT :limit
        """)
        
        result = await db.execute(
            sql, 
            {
                "query_embedding": query_embedding, 
                "limit": limit
            }
        )
        
        rows = result.fetchall()
        
        return [
            SearchResult(
                content=row.content,
                source=row.source,
                score=row.similarity_score,
                document_title=row.document_title
            )
            for row in rows
        ]
    
    @staticmethod
    async def get_documents(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Document]:
        """Get all documents"""
        query = select(Document).where(Document.is_active == True).offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def get_document(db: AsyncSession, document_id: str) -> Optional[Document]:
        """Get document by ID"""
        query = select(Document).where(Document.id == document_id, Document.is_active == True)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def delete_document(db: AsyncSession, document_id: str) -> bool:
        """Soft delete a document"""
        document = await DocumentService.get_document(db, document_id)
        if document:
            document.is_active = False
            await db.commit()
            return True
        return False 