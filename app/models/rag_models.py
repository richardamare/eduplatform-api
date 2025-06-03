from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, Text, ForeignKey, Integer, func
from pgvector.sqlalchemy import Vector
from datetime import datetime
from typing import List, Optional
from app.database import Base

class SourceFileDB(Base):
    __tablename__ = "source_files"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_path: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    
    # Relationships
    vectors: Mapped[List["VectorDB"]] = relationship("VectorDB", back_populates="source_file", cascade="all, delete-orphan")

class VectorDB(Base):
    __tablename__ = "vectors"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_file_id: Mapped[int] = mapped_column(Integer, ForeignKey("source_files.id"), nullable=False)
    vector_data: Mapped[Vector] = mapped_column(Vector(1536), nullable=False)  # OpenAI embedding size
    snippet: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    
    # Relationships
    source_file: Mapped["SourceFileDB"] = relationship("SourceFileDB", back_populates="vectors") 