# pyrefly: ignore-all-errors

from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import List

from app.database import Base


class WorkspaceDB(Base):
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )

    # Relationships
    chats: Mapped[List["ChatDB"]] = relationship(
        "ChatDB", back_populates="workspace", cascade="all, delete-orphan"
    )
    files: Mapped[List["SourceFileDB"]] = relationship(
        "SourceFileDB", back_populates="workspace", cascade="all, delete-orphan"
    )
