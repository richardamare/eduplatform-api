# pyrefly: ignore-all-errors

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, Text, ForeignKey, func, UUID
from app.database import Base
from datetime import datetime


class GeneratedContentDB(Base):
    __tablename__ = "generated_contents"

    id: Mapped[UUID] = mapped_column(UUID, primary_key=True)
    type: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    workspace_id: Mapped[UUID] = mapped_column(
        UUID, ForeignKey("workspaces.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )

    # Relationships
    workspace: Mapped["WorkspaceDB"] = relationship("WorkspaceDB")
