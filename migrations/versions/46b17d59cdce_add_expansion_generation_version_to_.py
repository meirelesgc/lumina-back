"""add_expansion_generation_version_to_applied_branches

Revision ID: 46b17d59cdce
Revises: 3505c2db872a
Create Date: 2026-09-22 12:02:55.968071

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '46b17d59cdce'
down_revision: Union[str, Sequence[str], None] = '3505c2db872a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('applied_branches', sa.Column('expansion_generation_version', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('applied_branches', 'expansion_generation_version')
