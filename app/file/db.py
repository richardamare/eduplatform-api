# pyrefly: ignore-all-errors

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, Text, ForeignKey, Integer, func
from pgvector.sqlalchemy import Vector
from app.database import Base
from datetime import datetime
from typing import List, Optional


class SourceFileDB(Base):
    __tablename__ = "source_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_path: Mapped[str] = mapped_column(
        Text, nullable=False, unique=True
    )  # Azure blob path
    file_name: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # Original filename
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)  # MIME type
    workspace_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("workspaces.id"), nullable=False
    )  # Workspace identifier
    file_size: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )  # File size in bytes
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Relationships
    workspace: Mapped["WorkspaceDB"] = relationship(
        "WorkspaceDB", back_populates="files"
    )
    vectors: Mapped[List["VectorDB"]] = relationship(
        "VectorDB", back_populates="source_file", cascade="all, delete-orphan"
    )


class VectorDB(Base):
    __tablename__ = "vectors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_file_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("source_files.id"), nullable=False
    )
    vector_data: Mapped[Vector] = mapped_column(
        Vector(1536), nullable=False
    )  # OpenAI embedding size
    content_text: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # Changed from snippet to content_text for consistency
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Relationships
    source_file: Mapped["SourceFileDB"] = relationship(
        "SourceFileDB", back_populates="vectors"
    )
