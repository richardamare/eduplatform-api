"""Initial migration with pgvector support

Revision ID: 134c0c282db2
Revises: 
Create Date: 2025-06-03 08:19:32.163347

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = '134c0c282db2'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable vector extension
    # op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # Create workspaces table
    op.create_table('workspaces',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create chats table
    op.create_table('chats',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('workspace_id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create messages table
    op.create_table('messages',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('chat_id', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['chat_id'], ['chats.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create attachments table with vector support
    op.create_table('attachments',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('azure_blob_path', sa.String(), nullable=False),
        sa.Column('workspace_id', sa.String(), nullable=False),
        sa.Column('content_vector', Vector(1536), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for better performance
    op.create_index('idx_chats_workspace_id', 'chats', ['workspace_id'])
    op.create_index('idx_messages_chat_id', 'messages', ['chat_id'])
    op.create_index('idx_attachments_workspace_id', 'attachments', ['workspace_id'])
    
    # Create vector similarity index for faster searches
    op.execute('CREATE INDEX ON attachments USING ivfflat (content_vector vector_cosine_ops) WITH (lists = 100)')


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_attachments_workspace_id', table_name='attachments')
    op.drop_index('idx_messages_chat_id', table_name='messages')
    op.drop_index('idx_chats_workspace_id', table_name='chats')
    
    # Drop tables
    op.drop_table('attachments')
    op.drop_table('messages')
    op.drop_table('chats')
    op.drop_table('workspaces')
    
    # Drop vector extension (optional, might be used by other apps)
    # op.execute('DROP EXTENSION IF EXISTS vector')
