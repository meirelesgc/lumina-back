"""add references to applied_branches

Revision ID: e93940cdeacb
Revises: e92898cdeacb
Create Date: 2026-08-13 19:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e93940cdeacb'
down_revision: Union[str, Sequence[str], None] = 'e92898cdeacb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('applied_branches', sa.Column('references', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('applied_branches', 'references')
