"""create advisorships table and document relation

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-19 00:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0007'
down_revision: Union[str, None] = '0006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create advisorships table
    op.create_table(
        'advisorships',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('advisor_id', sa.Uuid(), nullable=False),
        sa.Column('advisee_id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.Uuid(), nullable=True),
        sa.Column('role_type', sa.String(), nullable=False, server_default='MAIN_ADVISOR'),
        sa.Column('topic', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='ACTIVE'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.Uuid(), nullable=True),
        sa.Column('updated_by', sa.Uuid(), nullable=True),
        sa.Column('deleted_by', sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(['advisor_id'], ['users.id'], name='fk_advisorship_advisor_id'),
        sa.ForeignKeyConstraint(['advisee_id'], ['users.id'], name='fk_advisorship_advisee_id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name='fk_advisorship_project_id'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], name='fk_advisorships_created_by', use_alter=True),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], name='fk_advisorships_updated_by', use_alter=True),
        sa.ForeignKeyConstraint(['deleted_by'], ['users.id'], name='fk_advisorships_deleted_by', use_alter=True),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_index(
        'ix_uq_advisorship_active',
        'advisorships',
        ['advisor_id', 'advisee_id', 'project_id', 'role_type'],
        unique=True,
        postgresql_where=sa.text('deleted_at IS NULL'),
    )

    # 2. Add advisorship_id to documents
    op.add_column('documents', sa.Column('advisorship_id', sa.Uuid(), nullable=True))
    op.create_foreign_key(
        'fk_documents_advisorship_id',
        'documents',
        'advisorships',
        ['advisorship_id'],
        ['id'],
    )


def downgrade() -> None:
    op.drop_constraint('fk_documents_advisorship_id', 'documents', type_='foreignkey')
    op.drop_column('documents', 'advisorship_id')
    op.drop_index('ix_uq_advisorship_active', table_name='advisorships')
    op.drop_table('advisorships')
