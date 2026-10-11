"""remover_run_id_de_tree_suggestion_sessions

Revision ID: 7c1e4b9d2a30
Revises: 3ea3cae7c41f
Create Date: 2026-10-12 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c1e4b9d2a30'
down_revision: Union[str, Sequence[str], None] = '3ea3cae7c41f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column('tree_suggestion_sessions', 'run_id')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        'tree_suggestion_sessions',
        sa.Column('run_id', sa.Uuid(), nullable=True),
    )
