"""adicionar_excluded_rules_em_tree_suggestion_sessions

Revision ID: 3ea3cae7c41f
Revises: beeed5597df0
Create Date: 2026-10-10 21:04:33.431706

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '3ea3cae7c41f'
down_revision: Union[str, Sequence[str], None] = 'beeed5597df0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'tree_suggestion_sessions',
        sa.Column(
            'excluded_rules',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('tree_suggestion_sessions', 'excluded_rules')
