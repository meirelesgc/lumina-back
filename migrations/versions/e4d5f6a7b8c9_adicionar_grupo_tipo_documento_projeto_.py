"""adicionar grupo, tipo_documento, projeto_nome em documents

Revision ID: e4d5f6a7b8c9
Revises: a1b2c3d4e5f6
Create Date: 2026-06-23 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e4d5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('documents', sa.Column('grupo', sa.String(), nullable=True))
    op.add_column('documents', sa.Column('tipo_documento', sa.String(), nullable=True))
    op.add_column('documents', sa.Column('projeto_nome', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('documents', 'projeto_nome')
    op.drop_column('documents', 'tipo_documento')
    op.drop_column('documents', 'grupo')
