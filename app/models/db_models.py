from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, Text, ForeignKey, func, Integer
from pgvector.sqlalchemy import Vector
from datetime import datetime
from typing import List, Optional
from app.database import Base

class ChatDB(Base):
    __tablename__ = "chats"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    workspace_id: Mapped[str] = mapped_column(String, ForeignKey("workspaces.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    workspace: Mapped["WorkspaceDB"] = relationship("WorkspaceDB", back_populates="chats")
    messages: Mapped[List["MessageDB"]] = relationship("MessageDB", back_populates="chat", cascade="all, delete-orphan")

class MessageDB(Base):
    __tablename__ = "messages"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    chat_id: Mapped[str] = mapped_column(String, ForeignKey("chats.id"), nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)  # "user" or "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    
    # Relationships
    chat: Mapped["ChatDB"] = relationship("ChatDB", back_populates="messages")

class WorkspaceDB(Base):
    __tablename__ = "workspaces"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    chats: Mapped[List["ChatDB"]] = relationship("ChatDB", back_populates="workspace", cascade="all, delete-orphan")
    attachments: Mapped[List["AttachmentDB"]] = relationship("AttachmentDB", back_populates="workspace", cascade="all, delete-orphan")

class AttachmentDB(Base):
    __tablename__ = "attachments"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)  # file type/extension
    azure_blob_path: Mapped[str] = mapped_column(String, nullable=False)
    workspace_id: Mapped[str] = mapped_column(String, ForeignKey("workspaces.id"), nullable=False)
    content_vector: Mapped[Optional[Vector]] = mapped_column(Vector(1536), nullable=True)  # OpenAI embedding size
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    workspace: Mapped["WorkspaceDB"] = relationship("WorkspaceDB", back_populates="attachments")

class DataItemDB(Base):
    __tablename__ = "data_items"
   
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    workspace_id: Mapped[str] = mapped_column(String, ForeignKey("workspaces.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    workspace: Mapped["WorkspaceDB"] = relationship("WorkspaceDB") 