from typing import List, Optional, Tuple, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, func
from openai import AsyncAzureOpenAI
from app.models.rag_models import SourceFileDB, VectorDB
from app.models.rag import DocumentRecord, VectorSearchResult, ProcessingJob, ProcessingStatus
from app.config import settings
from datetime import datetime
import uuid
import asyncio
import logging

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self):
        self.openai_client = AsyncAzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version="2024-02-01"
        )
        # In-memory job tracking (in production, use Redis or database)
        self.processing_jobs: Dict[str, ProcessingJob] = {}
    
    def create_processing_job(self, file_name: str) -> ProcessingJob:
        """Create a new processing job and return job details."""
        job_id = str(uuid.uuid4())
        
        # Estimate processing time based on file size (rough estimate)
        if file_name.lower().endswith('.pdf'):
            estimated_time = "2-5 minutes for PDFs"
        elif file_name.lower().endswith(('.docx', '.doc')):
            estimated_time = "1-3 minutes for Word documents"
        else:
            estimated_time = "30 seconds - 2 minutes"
        
        job = ProcessingJob(
            job_id=job_id,
            file_name=file_name,
            status=ProcessingStatus.PENDING,
            message="Document uploaded successfully. Processing started.",
            created_at=datetime.utcnow()
        )
        
        self.processing_jobs[job_id] = job
        logger.info(f"Created processing job {job_id} for file {file_name}")
        return job
    
    def get_processing_job(self, job_id: str) -> Optional[ProcessingJob]:
        """Get processing job status."""
        return self.processing_jobs.get(job_id)
    
    def update_job_status(self, job_id: str, status: ProcessingStatus, message: str, **kwargs):
        """Update job status and additional fields."""
        if job_id in self.processing_jobs:
            job = self.processing_jobs[job_id]
            job.status = status
            job.message = message
            
            if status in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED]:
                job.completed_at = datetime.utcnow()
            
            # Update additional fields
            for key, value in kwargs.items():
                if hasattr(job, key):
                    setattr(job, key, value)
            
            logger.info(f"Updated job {job_id}: {status} - {message}")
    
    async def process_document_background(
        self, 
        job_id: str,
        file_content: bytes, 
        file_name: str,
        db: AsyncSession,
        replace_existing: bool = False
    ):
        """Process document in background with status updates."""
        try:
            from app.services.document_processor import DocumentProcessor
            
            # Update status to processing
            self.update_job_status(job_id, ProcessingStatus.PROCESSING, "Extracting text from document...")
            
            # Initialize document processor
            doc_processor = DocumentProcessor()
            
            # Extract text and create chunks
            chunks = doc_processor.process_file(file_content, file_name)
            
            if not chunks:
                self.update_job_status(
                    job_id, 
                    ProcessingStatus.FAILED, 
                    "No text content could be extracted from file",
                    error_details="File appears to be empty or unreadable"
                )
                return
            
            # Update status to vectorizing
            self.update_job_status(job_id, ProcessingStatus.PROCESSING, f"Creating vector embeddings for {len(chunks)} text chunks...")
            
            # Check if document already exists
            existing_count = await self.get_document_vector_count(db, file_name)
            
            if existing_count > 0 and not replace_existing:
                self.update_job_status(
                    job_id, 
                    ProcessingStatus.FAILED, 
                    f"Document already exists with {existing_count} vectors",
                    error_details="Use replace_existing=true to overwrite existing document"
                )
                return
            
            # Process chunks and store vectors
            if replace_existing:
                await self.delete_source_file(db, file_name)
            
            # Process chunks in batches to avoid overwhelming the API
            batch_size = 5  # Process 5 chunks at a time
            total_processed = 0
            
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]
                
                # Update progress
                progress_msg = f"Processing chunks {total_processed + 1}-{min(total_processed + len(batch), len(chunks))} of {len(chunks)}"
                self.update_job_status(job_id, ProcessingStatus.PROCESSING, progress_msg)
                
                # Process batch
                for chunk in batch:
                    record = DocumentRecord(
                        file_path=file_name,
                        content=chunk
                    )
                    await self.insert_document_record(db, record)
                    total_processed += 1
                
                # Small delay to prevent API rate limiting
                await asyncio.sleep(0.5)
            
            # Mark as completed
            self.update_job_status(
                job_id, 
                ProcessingStatus.COMPLETED, 
                f"Document processed successfully. Created {len(chunks)} searchable chunks.",
                chunks_created=len(chunks)
            )
            
            logger.info(f"Successfully processed document {file_name} in background job {job_id}")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Background processing failed for job {job_id}: {error_msg}")
            
            self.update_job_status(
                job_id, 
                ProcessingStatus.FAILED, 
                f"Processing failed: {error_msg}",
                error_details=error_msg
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
            model="text-embedding-3-small"
        )
        return response.data[0].embedding
    
    async def insert_document_record(self, db: AsyncSession, record: DocumentRecord) -> None:
        """Insert a document record with its vector data."""
        
        # Check if source file exists, if not create it
        stmt = select(SourceFileDB).where(SourceFileDB.file_path == record.file_path)
        result = await db.execute(stmt)
        source_file = result.scalar_one_or_none()
        
        if not source_file:
            # Create new source file - use merge to handle race conditions
            source_file = SourceFileDB(file_path=record.file_path)
            db.add(source_file)
            try:
                await db.flush()  # Get the ID
            except Exception as e:
                # Handle unique constraint violation (race condition)
                await db.rollback()
                # Try to fetch the existing record again
                stmt = select(SourceFileDB).where(SourceFileDB.file_path == record.file_path)
                result = await db.execute(stmt)
                source_file = result.scalar_one_or_none()
                if not source_file:
                    raise e  # Re-raise if it's not a duplicate key error
        
        # Generate embedding if not provided
        if not record.vector:
            record.vector = await self.get_embedding(record.content)
        
        # Convert vector to PostgreSQL format
        vector_str = "[" + ",".join(map(str, record.vector)) + "]"
        
        # Insert vector record using raw SQL to avoid serialization issues
        await db.execute(text("""
            INSERT INTO vectors (source_file_id, vector_data, snippet, created_at)
            VALUES (:source_file_id, :vector_data, :snippet, now())
        """), {
            'source_file_id': source_file.id,
            'vector_data': vector_str,
            'snippet': record.content
        })
        await db.commit()
    
    async def insert_document_with_chunks(
        self, 
        db: AsyncSession, 
        file_path: str, 
        text_chunks: List[str],
        replace_existing: bool = False
    ) -> None:
        """Insert a document split into multiple chunks."""
        
        # If replace_existing is True, delete existing vectors for this file first
        if replace_existing:
            await self.delete_source_file(db, file_path)
        
        # Check if document already exists and has vectors
        stmt = select(SourceFileDB).where(SourceFileDB.file_path == file_path)
        result = await db.execute(stmt)
        existing_file = result.scalar_one_or_none()
        
        if existing_file:
            # Check if it already has vectors
            vector_count_stmt = select(func.count(VectorDB.id)).where(VectorDB.source_file_id == existing_file.id)
            vector_count_result = await db.execute(vector_count_stmt)
            vector_count = vector_count_result.scalar()
            
            if vector_count > 0 and not replace_existing:
                print(f"Warning: Document {file_path} already exists with {vector_count} vectors. Skipping.")
                return
        
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
        
        # First, let's check if we have any vectors at all
        count_sql = text("SELECT COUNT(*) FROM vectors")
        count_result = await db.execute(count_sql)
        vector_count = count_result.scalar()
        logger.info(f"Total vectors in database: {vector_count}")
        
        # Execute similarity search
        # Note: For normalized vectors (like OpenAI embeddings), cosine distance = 2 * (1 - cosine_similarity)
        # So: cosine_similarity = 1 - (cosine_distance / 2)
        # Range: distance 0 (identical) -> similarity 1, distance 2 (opposite) -> similarity 0
        sql = text("""
            SELECT 
                v.id, 
                s.file_path, 
                v.snippet,
                1 - (CAST(v.vector_data AS vector) <=> CAST(:query_vector AS vector)) / 2.0 as similarity,
                CAST(v.vector_data AS vector) <=> CAST(:query_vector AS vector) as distance
            FROM vectors v
            JOIN source_files s ON s.id = v.source_file_id
            ORDER BY CAST(v.vector_data AS vector) <=> CAST(:query_vector AS vector)
            LIMIT :limit;
        """)
        
        result = await db.execute(sql, {
            "query_vector": query_vector_str,
            "limit": limit
        })
        
        rows = result.fetchall()
        
        # Log results for debugging
        logger.info(f"Query: '{query_text}'")
        logger.info(f"Found {len(rows)} results before similarity filtering")
        for i, row in enumerate(rows):
            logger.info(f"Result {i+1}: distance={row[4]:.4f}, similarity={row[3]:.4f}, snippet='{row[2][:50]}...'")
        
        # Filter by minimum similarity
        filtered_results = [
            VectorSearchResult(
                id=row[0],
                file_path=row[1], 
                snippet=row[2],
                similarity=float(row[3])
            )
            for row in rows if float(row[3]) >= min_similarity
        ]
        
        logger.info(f"Returning {len(filtered_results)} results after similarity filtering (min_similarity={min_similarity})")
        return filtered_results
    
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
    
    async def document_exists(self, db: AsyncSession, file_path: str) -> bool:
        """Check if a document already exists in the database."""
        stmt = select(SourceFileDB).where(SourceFileDB.file_path == file_path)
        result = await db.execute(stmt)
        return result.scalar_one_or_none() is not None
    
    async def get_document_vector_count(self, db: AsyncSession, file_path: str) -> int:
        """Get the number of vectors for a specific document."""
        stmt = select(SourceFileDB).where(SourceFileDB.file_path == file_path)
        result = await db.execute(stmt)
        source_file = result.scalar_one_or_none()
        
        if not source_file:
            return 0
            
        vector_count_stmt = select(func.count(VectorDB.id)).where(VectorDB.source_file_id == source_file.id)
        vector_count_result = await db.execute(vector_count_stmt)
        return vector_count_result.scalar()
    
    async def upsert_document_with_chunks(
        self, 
        db: AsyncSession, 
        file_path: str, 
        text_chunks: List[str]
    ) -> dict:
        """Upsert a document - replace if exists, insert if new."""
        
        existing_vector_count = await self.get_document_vector_count(db, file_path)
        
        if existing_vector_count > 0:
            # Delete existing vectors first
            await self.delete_source_file(db, file_path)
            action = "replaced"
        else:
            action = "created"
        
        # Insert new chunks
        await self.insert_document_with_chunks(db, file_path, text_chunks, replace_existing=False)
        
        return {
            "action": action,
            "file_path": file_path,
            "chunks_count": len(text_chunks),
            "previous_vector_count": existing_vector_count
        } 