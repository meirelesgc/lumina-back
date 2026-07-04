"""add responsibles column to project_documents

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-30 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = '0003'
down_revision: Union[str, None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('project_documents', sa.Column('responsibles', JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column('project_documents', 'responsibles')
