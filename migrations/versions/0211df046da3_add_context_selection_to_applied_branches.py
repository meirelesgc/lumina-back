"""add_context_selection_to_applied_branches

Revision ID: 0211df046da3
Revises: 7c1e4b9d2a30
Create Date: 2026-10-17 06:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0211df046da3'
down_revision: Union[str, Sequence[str], None] = '7c1e4b9d2a30'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'applied_branches',
        sa.Column(
            'context_selection',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('applied_branches', 'context_selection')
