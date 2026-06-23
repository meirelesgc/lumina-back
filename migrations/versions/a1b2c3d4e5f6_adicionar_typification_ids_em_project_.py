"""adicionar typification_ids em project_documents

Revision ID: a1b2c3d4e5f6
Revises: fce075e65e07
Create Date: 2026-06-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'd9c4b2f1a5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('project_documents', sa.Column('typification_ids', JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column('project_documents', 'typification_ids')
