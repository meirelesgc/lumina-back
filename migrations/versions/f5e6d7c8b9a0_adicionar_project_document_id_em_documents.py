"""adicionar project_document_id em documents

Revision ID: f5e6d7c8b9a0
Revises: e4d5f6a7b8c9
Create Date: 2026-06-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f5e6d7c8b9a0'
down_revision: Union[str, Sequence[str], None] = 'e4d5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('documents',
        sa.Column('project_document_id', sa.Uuid(), nullable=True)
    )
    op.create_foreign_key(
        'fk_documents_project_document_id',
        'documents', 'project_documents',
        ['project_document_id'], ['id'],
    )


def downgrade() -> None:
    op.drop_constraint('fk_documents_project_document_id', 'documents', type_='foreignkey')
    op.drop_column('documents', 'project_document_id')
