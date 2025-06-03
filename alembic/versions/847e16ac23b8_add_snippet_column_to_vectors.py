"""add_snippet_column_to_vectors

Revision ID: 847e16ac23b8
Revises: 6a9a626a97c9
Create Date: 2025-06-03 09:34:17.918345

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '847e16ac23b8'
down_revision: Union[str, None] = '6a9a626a97c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add snippet column to vectors table
    op.add_column('vectors', sa.Column('snippet', sa.Text(), nullable=False, server_default=''))


def downgrade() -> None:
    # Remove snippet column from vectors table
    op.drop_column('vectors', 'snippet')
