# pyrefly: ignore-all-errors

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from app.file.db import VectorDB, SourceFileDB


class VectorRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, payload: VectorDB) -> VectorDB:
        vector = VectorDB(
            id=str(uuid.uuid4()),
            source_file_id=payload.source_file_id,
            vector_data=payload.vector_data,
            content_text=payload.content_text,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(vector)
        await self.db.commit()
        await self.db.refresh(vector)
        return vector

    async def get_by_source_file(self, source_file_id: str) -> List[VectorDB]:
        result = await self.db.execute(
            select(VectorDB).where(VectorDB.source_file_id == source_file_id)
        )
        vectors = result.scalars().all()
        return [VectorDB(**vector.__dict__) for vector in vectors]

    async def delete_by_source_file(self, source_file_id: str):
        await self.db.execute(
            delete(VectorDB).where(VectorDB.source_file_id == source_file_id)
        )
        await self.db.commit()

    async def search_similar_vectors(
        self,
        query_embedding: List[float],
        workspace_id: Optional[str] = None,
        limit: int = 5,
        min_similarity: float = 0.0,
    ) -> List[VectorSearchResult]:
        """Search for similar vectors using cosine similarity."""

        # Build SQL with optional workspace filter
        where_clause = f"WHERE cosine_similarity(v.vector_data, '{query_embedding}'::vector) >= {min_similarity}"
        if workspace_id:
            where_clause += f" AND sf.workspace_id = '{workspace_id}'"

        sql = text(
            f"""
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
            LIMIT {limit}
        """
        )

        result = await self.db.execute(sql)

        search_results = [
            VectorSearchResult(
                vector_id=row.id,
                similarity=row.similarity,
                content_text=row.content_text,
                file_path=row.file_path,
            )
            for row in result
        ]

        return search_results

    async def get_vector_count_by_file_path(self, file_path: str) -> int:
        sql = text(
            """
            SELECT COUNT(v.id) 
            FROM vectors v
            JOIN source_files sf ON v.source_file_id = sf.id
            WHERE sf.file_path = :file_path
        """
        )
        result = await self.db.execute(sql, {"file_path": file_path})
        sc = result.scalar()
        if sc is None:
            return 0
        return sc


class SourceFileRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, payload: SourceFileDB) -> SourceFileDB:
        source_file = SourceFileDB(
            id=str(uuid.uuid4()),
            file_path=payload.file_path,
            file_name=payload.file_name,
            content_type=payload.content_type,
            workspace_id=payload.workspace_id,
            file_size=payload.file_size,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.db.add(source_file)
        await self.db.commit()
        await self.db.refresh(source_file)
        return source_file

    async def get_by_workspace(self, workspace_id: str) -> List[SourceFileDB]:
        result = await self.db.execute(
            select(SourceFileDB).where(SourceFileDB.workspace_id == workspace_id)
        )
        source_files = result.scalars().all()
        return [SourceFileDB(**source_file.__dict__) for source_file in source_files]

    async def get_by_id(self, source_file_id: str) -> Optional[SourceFileDB]:
        result = await self.db.execute(
            select(SourceFileDB).where(SourceFileDB.id == source_file_id)
        )
        source_file = result.scalar_one_or_none()
        return SourceFileDB(**source_file.__dict__) if source_file else None

    async def delete_by_file_path(self, file_path: str):
        delete_vectors_stmt = text(
            """
            DELETE FROM vectors 
            WHERE source_file_id IN (
                SELECT id FROM source_files WHERE file_path = :file_path
            )
        """
        )

        delete_source_file_stmt = text(
            """
            DELETE FROM source_files WHERE file_path = :file_path
        """
        )

        await self.db.execute(delete_vectors_stmt, {"file_path": file_path})
        await self.db.execute(delete_source_file_stmt, {"file_path": file_path})
        await self.db.commit()

    async def get_by_file_path(self, file_path: str) -> Optional[SourceFileDB]:
        result = await self.db.execute(
            select(SourceFileDB).where(SourceFileDB.file_path == file_path)
        )
        source_file = result.scalar_one_or_none()
        return SourceFileDB(**source_file.__dict__) if source_file else None

    async def exists(self, file_path: str) -> bool:
        stmt = select(SourceFileDB).where(SourceFileDB.file_path == file_path)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_all(self) -> List[SourceFileDB]:
        result = await self.db.execute(select(SourceFileDB))
        source_files = result.scalars().all()
        return [SourceFileDB(**source_file.__dict__) for source_file in source_files]
