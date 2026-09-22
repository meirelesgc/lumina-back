"""add_section_requirement_version_to_applied_branches

Revision ID: fa603197d76f
Revises: 08c36ece1789
Create Date: 2026-09-22 12:31:20.523205

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fa603197d76f'
down_revision: Union[str, Sequence[str], None] = '08c36ece1789'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('applied_branches', sa.Column('section_requirement_version', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('applied_branches', 'section_requirement_version')
