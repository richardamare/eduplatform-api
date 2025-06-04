from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from openai import AsyncAzureOpenAI
from app.models.rag_models import SourceFileDB, VectorDB
from app.models.rag import VectorSearchResult, SourceFileDto, CreateSourceFilePayload
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self):
        self.openai_client = AsyncAzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version
        )
    
    async def ensure_database_setup(self, db: AsyncSession) -> None:
        """Ensures pgvector extension and cosine similarity function exist."""
        
        # Create pgvector extension
        await db.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        
        # Create cosine similarity function that returns actual similarity (0-1 range)
        cosine_similarity_sql = """
        CREATE OR REPLACE FUNCTION cosine_similarity(a vector, b vector) 
        RETURNS float AS $$
        BEGIN
            RETURN 1 - (a <=> b) / 2.0;
        END;
        $$ LANGUAGE plpgsql IMMUTABLE STRICT;
        """
        
        await db.execute(text(cosine_similarity_sql))
        await db.commit()
    
    async def get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using Azure OpenAI."""
        response = await self.openai_client.embeddings.create(
            input=text,
            model=settings.azure_openai_embedding_model
        )
        return response.data[0].embedding
    
    async def create_source_file(
        self, 
        db: AsyncSession, 
        payload: CreateSourceFilePayload
    ) -> SourceFileDB:
        """Create a new source file record."""
        source_file = SourceFileDB(
            file_path=payload.file_path,
            file_name=payload.file_name,
            content_type=payload.content_type,
            workspace_id=payload.workspace_id,
            file_size=payload.file_size
        )
        db.add(source_file)
        await db.flush()
        return source_file
    
    async def insert_document_with_chunks(
        self, 
        db: AsyncSession, 
        file_path: str,
        file_name: str,
        content_type: str,
        workspace_id: str,
        text_chunks: List[str],
        file_size: Optional[int] = None,
        replace_existing: bool = False
    ) -> SourceFileDto:
        """Insert document with text chunks and generate embeddings."""
        
        # Check if source file exists
        stmt = select(SourceFileDB).where(SourceFileDB.file_path == file_path)
        result = await db.execute(stmt)
        source_file = result.scalar_one_or_none()
        
        if source_file and replace_existing:
            # Delete existing vectors for this file
            await self.delete_source_file(db, file_path)
            await db.flush()
            source_file = None
        elif source_file and not replace_existing:
            raise ValueError(f"File already exists: {file_path}")
        
        if not source_file:
            # Create new source file
            payload = CreateSourceFilePayload(
                file_path=file_path,
                file_name=file_name,
                content_type=content_type,
                workspace_id=workspace_id,
                file_size=file_size
            )
            source_file = await self.create_source_file(db, payload)
        
        # Insert text chunks as vectors
        for chunk in text_chunks:
            # Generate embedding
            embedding = await self.get_embedding(chunk)
            
            # Create vector record
            vector_record = VectorDB(
                source_file_id=source_file.id,
                content_text=chunk,
                vector_data=embedding
            )
            db.add(vector_record)
        
        await db.commit()
        
        # Return SourceFileDto with chunks count
        return SourceFileDto(
            id=source_file.id,
            file_path=source_file.file_path,
            file_name=source_file.file_name,
            content_type=source_file.content_type,
            workspace_id=source_file.workspace_id,
            file_size=source_file.file_size,
            created_at=source_file.created_at,
            chunks_count=len(text_chunks)
        )
    
    async def search_similar_vectors(
        self, 
        db: AsyncSession, 
        query_text: str, 
        workspace_id: Optional[str] = None,
        limit: int = 5,
        min_similarity: float = 0.0
    ) -> List[VectorSearchResult]:
        """Search for similar vectors using cosine similarity."""
        
                # Generate embedding for query
        query_embedding = await self.get_embedding(query_text)
        
        # Build SQL with optional workspace filter
        where_clause = f"WHERE cosine_similarity(v.vector_data, '{query_embedding}'::vector) >= {min_similarity}"
        if workspace_id:
            where_clause += f" AND sf.workspace_id = '{workspace_id}'"
        
        sql = text(f"""
            SELECT 
                v.id,
                v.content_text,
                sf.file_path,
                sf.file_name,
                cosine_similarity(v.vector_data, '{query_embedding}'::vector) as similarity
            FROM vectors v
            JOIN source_files sf ON v.source_file_id = sf.id
            {where_clause}
            ORDER BY similarity DESC
            LIMIT 5
        """)

        print('sql', sql)
        
        # params = {
        #     "query_vector": str(query_embedding),  # Convert list to string for PostgreSQL
        #     "min_similarity": min_similarity,
        #     "limit": limit
        # }
        # if workspace_id:
        #     params["workspace_id"] = workspace_id
        
        result = await db.execute(sql)
        
        search_results = []
        for row in result:
            search_results.append(VectorSearchResult(
                vector_id=row.id,
                similarity=row.similarity,
                snippet=row.content_text,
                file_path=row.file_path
            ))
        
        return search_results
    
    async def get_workspace_source_files(self, db: AsyncSession, workspace_id: str) -> List[SourceFileDto]:
        """Get all source files for a workspace."""
        stmt = select(SourceFileDB).where(SourceFileDB.workspace_id == workspace_id)
        result = await db.execute(stmt)
        source_files = result.scalars().all()
        
        # Convert to DTOs and get chunk counts
        file_dtos = []
        for sf in source_files:
            # Get vector count
            chunks_count = await self.get_document_vector_count(db, sf.file_path)
            
            file_dtos.append(SourceFileDto(
                id=sf.id,
                file_path=sf.file_path,
                file_name=sf.file_name,
                content_type=sf.content_type,
                workspace_id=sf.workspace_id,
                file_size=sf.file_size,
                created_at=sf.created_at,
                chunks_count=chunks_count
            ))
        
        return file_dtos
    
    async def get_all_source_files(self, db: AsyncSession) -> List[tuple]:
        """Get all source files."""
        stmt = select(SourceFileDB.id, SourceFileDB.file_path, SourceFileDB.file_name, SourceFileDB.workspace_id)
        result = await db.execute(stmt)
        return result.all()
    
    async def delete_source_file(self, db: AsyncSession, file_path: str) -> bool:
        """Delete a source file and its vectors."""
        try:
            # Delete vectors first
            stmt = text("""
                DELETE FROM vectors 
                WHERE source_file_id IN (
                    SELECT id FROM source_files WHERE file_path = :file_path
                )
            """)
            await db.execute(stmt, {"file_path": file_path})
            
            # Delete source file
            stmt = text("DELETE FROM source_files WHERE file_path = :file_path")
            await db.execute(stmt, {"file_path": file_path})
            
            await db.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting source file {file_path}: {e}")
            await db.rollback()
            return False
    
    async def document_exists(self, db: AsyncSession, file_path: str) -> bool:
        """Check if a document exists."""
        stmt = select(SourceFileDB).where(SourceFileDB.file_path == file_path)
        result = await db.execute(stmt)
        return result.scalar_one_or_none() is not None
    
    async def get_document_vector_count(self, db: AsyncSession, file_path: str) -> int:
        """Get vector count for a document."""
        sql = text("""
            SELECT COUNT(v.id) 
            FROM vectors v
            JOIN source_files sf ON v.source_file_id = sf.id
            WHERE sf.file_path = :file_path
        """)
        result = await db.execute(sql, {"file_path": file_path})
        return result.scalar() or 0 