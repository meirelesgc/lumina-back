"""add source to document, context_text to chat_conversations

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('documents', sa.Column('source', sa.String(), nullable=True, server_default='manual'))
    op.add_column('chat_conversations', sa.Column('context_text', sa.Text(), nullable=True))
    op.add_column('project_documents', sa.Column('responsibles', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('project_documents', 'responsibles')
    op.drop_column('chat_conversations', 'context_text')
    op.drop_column('documents', 'source')
