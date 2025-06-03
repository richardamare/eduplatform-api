from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from openai import AsyncAzureOpenAI
from app.models.rag_models import SourceFileDB, VectorDB
from app.models.rag import DocumentRecord, VectorSearchResult
from app.config import settings

class RAGService:
    def __init__(self):
        self.openai_client = AsyncAzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version="2024-02-01"
        )
    
    async def ensure_database_setup(self, db: AsyncSession) -> None:
        """Ensures pgvector extension and cosine similarity function exist."""
        
        # Create pgvector extension
        await db.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        
        # Create cosine similarity function
        cosine_similarity_sql = """
        CREATE OR REPLACE FUNCTION cosine_similarity(a vector, b vector) 
        RETURNS float AS $$
        BEGIN
            RETURN (a <=> b);
        END;
        $$ LANGUAGE plpgsql IMMUTABLE STRICT;
        """
        
        await db.execute(text(cosine_similarity_sql))
        await db.commit()
    
    async def get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using Azure OpenAI."""
        response = await self.openai_client.embeddings.create(
            input=text,
            model="text-embedding-3-small"
        )
        return response.data[0].embedding
    
    async def insert_document_record(self, db: AsyncSession, record: DocumentRecord) -> None:
        """Insert a document record with its vector data."""
        
        # Check if source file exists
        stmt = select(SourceFileDB).where(SourceFileDB.file_path == record.file_path)
        result = await db.execute(stmt)
        source_file = result.scalar_one_or_none()
        
        if not source_file:
            # Create new source file
            source_file = SourceFileDB(file_path=record.file_path)
            db.add(source_file)
            await db.flush()  # Get the ID
        
        # Generate embedding if not provided
        if not record.vector:
            record.vector = await self.get_embedding(record.content)
        
        # Insert vector record using raw SQL to avoid serialization issues
        await db.execute(text("""
            INSERT INTO vectors (source_file_id, vector_data, snippet, created_at)
            VALUES (:source_file_id, :vector_data, :snippet, now())
        """), {
            'source_file_id': source_file.id,
            'vector_data': record.vector,
            'snippet': record.content
        })
        await db.commit()
    
    async def insert_document_with_chunks(
        self, 
        db: AsyncSession, 
        file_path: str, 
        text_chunks: List[str]
    ) -> None:
        """Insert a document split into multiple chunks."""
        
        for chunk in text_chunks:
            record = DocumentRecord(
                file_path=file_path,
                content=chunk
            )
            await self.insert_document_record(db, record)
    
    async def search_similar_vectors(
        self, 
        db: AsyncSession, 
        query_text: str, 
        limit: int = 5,
        min_similarity: float = 0.0
    ) -> List[VectorSearchResult]:
        """Search for similar vectors using cosine similarity."""
        
        # Generate query embedding
        query_vector = await self.get_embedding(query_text)
        
        # Convert query vector to PostgreSQL vector string format
        query_vector_str = "[" + ",".join(map(str, query_vector)) + "]"
        
        # Execute similarity search
        sql = text("""
            SELECT 
                v.id, 
                s.file_path, 
                v.snippet,
                1 - (CAST(v.vector_data AS vector) <=> CAST(:query_vector AS vector)) as similarity
            FROM vectors v
            JOIN source_files s ON s.id = v.source_file_id
            WHERE (1 - (CAST(v.vector_data AS vector) <=> CAST(:query_vector AS vector))) >= :min_similarity
            ORDER BY CAST(v.vector_data AS vector) <=> CAST(:query_vector AS vector)
            LIMIT :limit;
        """)
        
        result = await db.execute(sql, {
            "query_vector": query_vector_str,
            "limit": limit,
            "min_similarity": min_similarity
        })
        
        rows = result.fetchall()
        
        return [
            VectorSearchResult(
                id=row[0],
                file_path=row[1], 
                snippet=row[2],
                similarity=float(row[3])
            )
            for row in rows
        ]
    
    async def get_document_record_by_id(self, db: AsyncSession, vector_id: int) -> Optional[DocumentRecord]:
        """Retrieve a document record by vector ID."""
        
        stmt = select(VectorDB, SourceFileDB).join(
            SourceFileDB, VectorDB.source_file_id == SourceFileDB.id
        ).where(VectorDB.id == vector_id)
        
        result = await db.execute(stmt)
        row = result.first()
        
        if not row:
            return None
        
        vector_db, source_file_db = row
        
        return DocumentRecord(
            id=vector_db.id,
            file_path=source_file_db.file_path,
            content=vector_db.snippet
        )
    
    async def get_all_source_files(self, db: AsyncSession) -> List[Tuple[int, str]]:
        """Get all source files."""
        stmt = select(SourceFileDB.id, SourceFileDB.file_path)
        result = await db.execute(stmt)
        return [(row[0], row[1]) for row in result.fetchall()]
    
    async def get_all_vectors(self, db: AsyncSession) -> List[Tuple[int, int, str, str]]:
        """Get all vectors with their data."""
        sql = text("SELECT id, source_file_id, snippet, vector_data FROM vectors")
        result = await db.execute(sql)
        rows = result.fetchall()
        
        return [
            (
                row[0],  # id
                row[1],  # source_file_id  
                row[2],  # snippet
                str(row[3])[:50] + "..." if len(str(row[3])) > 50 else str(row[3])  # truncated vector_data
            )
            for row in rows
        ]
    
    async def delete_source_file(self, db: AsyncSession, file_path: str) -> bool:
        """Delete a source file and all its vectors."""
        stmt = select(SourceFileDB).where(SourceFileDB.file_path == file_path)
        result = await db.execute(stmt)
        source_file = result.scalar_one_or_none()
        
        if source_file:
            await db.delete(source_file)
            await db.commit()
            return True
        return False 