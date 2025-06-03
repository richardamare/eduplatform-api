from logging.config import fileConfig
import os
import sys

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, Text, ForeignKey, Integer, func
from pgvector.sqlalchemy import Vector
from datetime import datetime
from typing import List, Optional

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class Base(DeclarativeBase):
    pass

# Define models directly here to avoid import conflicts
class WorkspaceDB(Base):
    __tablename__ = "workspaces"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

class ChatDB(Base):
    __tablename__ = "chats"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    workspace_id: Mapped[str] = mapped_column(String, ForeignKey("workspaces.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

class MessageDB(Base):
    __tablename__ = "messages"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    chat_id: Mapped[str] = mapped_column(String, ForeignKey("chats.id"), nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

class AttachmentDB(Base):
    __tablename__ = "attachments"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    azure_blob_path: Mapped[str] = mapped_column(String, nullable=False)
    workspace_id: Mapped[str] = mapped_column(String, ForeignKey("workspaces.id"), nullable=False)
    content_vector: Mapped[Optional[Vector]] = mapped_column(Vector(1536), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

# RAG models
class SourceFileDB(Base):
    __tablename__ = "source_files"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_path: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

class VectorDB(Base):
    __tablename__ = "vectors"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_file_id: Mapped[int] = mapped_column(Integer, ForeignKey("source_files.id"), nullable=False)
    vector_data: Mapped[Vector] = mapped_column(Vector(1536), nullable=False)
    snippet: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    database_url = os.getenv("DATABASE_URL", "")
    # Convert async URL to sync for alembic
    if database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Override the sqlalchemy.url with the actual environment variable
    configuration = config.get_section(config.config_ini_section, {})
    database_url = os.getenv("DATABASE_URL", "")
    # Convert async URL to sync for alembic
    if database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    configuration["sqlalchemy.url"] = database_url
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
