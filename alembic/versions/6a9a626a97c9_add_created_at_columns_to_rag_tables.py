"""Add created_at columns to RAG tables

Revision ID: 6a9a626a97c9
Revises: 001_add_rag_tables
Create Date: 2025-06-03 09:22:11.409741

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6a9a626a97c9'
down_revision: Union[str, None] = '001_add_rag_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add created_at column to source_files table if it doesn't exist
    op.add_column('source_files', sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False))
    
    # Add created_at column to vectors table if it doesn't exist  
    op.add_column('vectors', sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False))


def downgrade() -> None:
    # Remove created_at column from vectors table
    op.drop_column('vectors', 'created_at')
    
    # Remove created_at column from source_files table
    op.drop_column('source_files', 'created_at')
