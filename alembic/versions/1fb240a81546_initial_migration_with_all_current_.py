"""Initial migration with all current models

Revision ID: 1fb240a81546
Revises:
Create Date: 2025-06-08 10:26:09.176146

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pgvector.sqlalchemy


# revision identifiers, used by Alembic.
revision: str = "1fb240a81546"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create cosine similarity function that returns actual similarity (0-1 range)
    cosine_similarity_sql = """
    CREATE OR REPLACE FUNCTION cosine_similarity(a vector, b vector) 
    RETURNS float AS $$
    BEGIN
        RETURN 1 - (a <=> b) / 2.0;
    END;
    $$ LANGUAGE plpgsql IMMUTABLE STRICT;
    """
    op.execute(cosine_similarity_sql)

    op.create_table(
        "workspaces",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "chats",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "generated_contents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "source_files",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("chat_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["chat_id"],
            ["chats.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "vectors",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_file_id", sa.UUID(), nullable=False),
        sa.Column("vector_data", pgvector.sqlalchemy.Vector(dim=1536), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_file_id"],
            ["source_files.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("vectors")
    op.drop_table("messages")
    op.drop_table("source_files")
    op.drop_table("generated_contents")
    op.drop_table("chats")
    op.drop_table("workspaces")
    op.execute("DROP FUNCTION IF EXISTS cosine_similarity(vector, vector)")
