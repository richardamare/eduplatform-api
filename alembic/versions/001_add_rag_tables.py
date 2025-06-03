"""Add RAG tables for vector storage

Revision ID: 001_add_rag_tables
Revises: 134c0c282db2
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = '001_add_rag_tables'
down_revision = '134c0c282db2'
branch_labels = None
depends_on = None


def upgrade():
    # Create source_files table
    op.create_table('source_files',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('file_path', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('file_path')
    )
    
    # Create vectors table
    op.create_table('vectors',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('source_file_id', sa.Integer(), nullable=False),
        sa.Column('vector_data', Vector(1536), nullable=False),
        sa.Column('snippet', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['source_file_id'], ['source_files.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('vectors')
    op.drop_table('source_files') 