import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from openai import AsyncAzureOpenAI

from app.database import async_session
from app.models.rag_models import SourceFileDB, VectorDB
from app.models.rag import VectorSearchResult, SourceFileDto, CreateSourceFilePayload
from app.services.repositories import SourceFileRepository, VectorRepository
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAGService:
    def __init__(self):
        if not all(
            [
                settings.azure_openai_endpoint,
                settings.azure_openai_api_key,
                settings.azure_openai_api_version,
                settings.azure_openai_embedding_model,
            ]
        ):
            logger.error("Azure OpenAI configuration is not set")
            raise ValueError("Azure OpenAI configuration is not set")

        self.openai_client = AsyncAzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )

        self.db = async_session()
        self.source_file_repository = SourceFileRepository(self.db)
        self.vector_repository = VectorRepository(self.db)

    async def ensure_database_setup(self) -> None:
        """Ensures pgvector extension and cosine similarity function exist."""

        # Create pgvector extension
        await self.db.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))

        # Create cosine similarity function that returns actual similarity (0-1 range)
        cosine_similarity_sql = """
        CREATE OR REPLACE FUNCTION cosine_similarity(a vector, b vector) 
        RETURNS float AS $$
        BEGIN
            RETURN 1 - (a <=> b) / 2.0;
        END;
        $$ LANGUAGE plpgsql IMMUTABLE STRICT;
        """

        await self.db.execute(text(cosine_similarity_sql))
        await self.db.commit()

    async def get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using Azure OpenAI."""
        response = await self.openai_client.embeddings.create(
            input=text, model=settings.azure_openai_embedding_model
        )
        return response.data[0].embedding

    async def insert_document_with_chunks(
        self,
        file_path: str,
        file_name: str,
        content_type: str,
        workspace_id: str,
        text_chunks: List[str],
        file_size: Optional[int] = None,
        replace_existing: bool = False,
    ) -> SourceFileDto:
        """Insert document with text chunks and generate embeddings."""

        source_file = await self.source_file_repository.get_by_file_path(file_path)

        if source_file and replace_existing:
            await self.source_file_repository.delete_by_file_path(file_path)
            source_file = None
        elif source_file and not replace_existing:
            logger.error(f"File already exists: {file_path}")
            raise ValueError(f"File already exists: {file_path}")

        if not source_file:
            # Create new source file
            source_file = await self.source_file_repository.create(
                SourceFileDB(
                    file_name=file_name,
                    file_path=file_path,
                    content_type=content_type,
                    workspace_id=workspace_id,
                    file_size=file_size,
                )
            )

        # Insert text chunks as vectors
        for chunk in text_chunks:
            embedding = await self.get_embedding(chunk)
            await self.vector_repository.create(
                VectorDB(
                    source_file_id=source_file.id,
                    content_text=chunk,
                    vector_data=embedding,
                )
            )

        # Return SourceFileDto with chunks count
        return SourceFileDto(
            id=source_file.id,
            file_path=source_file.file_path,
            file_name=source_file.file_name,
            content_type=source_file.content_type,
            workspace_id=source_file.workspace_id,
            file_size=source_file.file_size,
            created_at=source_file.created_at,
            chunks_count=len(text_chunks),
        )

    async def search_similar_vectors(
        self,
        query_text: str,
        workspace_id: str,
        limit: int = 5,
        min_similarity: float = 0.0,
    ) -> List[VectorSearchResult]:
        """Search for similar vectors using cosine similarity."""

        # Generate embedding for query
        query_embedding = await self.get_embedding(query_text)

        search_results = await self.vector_repository.search_similar_vectors(
            query_embedding=query_embedding,
            workspace_id=workspace_id,
            limit=limit,
            min_similarity=min_similarity,
        )

        return search_results

    async def get_source_files_by_workspace_id(
        self, workspace_id: str
    ) -> List[SourceFileDto]:
        """Get all source files for a workspace."""

        source_files = await self.source_file_repository.get_by_workspace(workspace_id)

        return [
            SourceFileDto(
                id=sf.id,
                file_path=sf.file_path,
                file_name=sf.file_name,
                content_type=sf.content_type,
                workspace_id=sf.workspace_id,
                file_size=sf.file_size,
                created_at=sf.created_at,
                chunks_count=None,
            )
            for sf in source_files
        ]

    async def get_all_source_files(self) -> List[SourceFileDto]:
        """Get all source files."""

        all_source_files = await self.source_file_repository.get_all()

        return [
            SourceFileDto(
                id=sf.id,
                file_path=sf.file_path,
                file_name=sf.file_name,
                content_type=sf.content_type,
                workspace_id=sf.workspace_id,
                file_size=sf.file_size,
                created_at=sf.created_at,
                chunks_count=None,
            )
            for sf in all_source_files
        ]

    async def document_exists(self, file_path: str) -> bool:
        """Check if a document exists."""

        return await self.source_file_repository.exists(file_path)

    async def get_vector_count(self, file_path: str) -> int:
        """Get vector count for a document."""

        return await self.vector_repository.get_vector_count_by_file_path(file_path)


rag_service = RAGService()
