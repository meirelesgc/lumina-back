"""adicionar document_group_id e document_group_item_id a typifications

Revision ID: ad7d5e73cc1f
Revises: 949464c31090
Create Date: 2026-06-22 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'ad7d5e73cc1f'
down_revision: Union[str, Sequence[str], None] = '949464c31090'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('typifications', sa.Column('document_group_id', sa.Uuid(), nullable=True))
    op.add_column('typifications', sa.Column('document_group_item_id', sa.Uuid(), nullable=True))


def downgrade() -> None:
    op.drop_column('typifications', 'document_group_item_id')
    op.drop_column('typifications', 'document_group_id')
