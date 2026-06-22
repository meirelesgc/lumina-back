"""criar tabela projects

Revision ID: e7f3c927d8e1
Revises: b2e8a41f6c3d
Create Date: 2026-06-22 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e7f3c927d8e1'
down_revision: Union[str, Sequence[str], None] = 'b2e8a41f6c3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('projects',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='INICIADO'),
        sa.Column('document_group_id', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.Uuid(), nullable=True),
        sa.Column('updated_by', sa.Uuid(), nullable=True),
        sa.Column('deleted_by', sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(['document_group_id'], ['document_groups.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], name='fk_projects_created_by', use_alter=True),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], name='fk_projects_updated_by', use_alter=True),
        sa.ForeignKeyConstraint(['deleted_by'], ['users.id'], name='fk_projects_deleted_by', use_alter=True),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('projects')
