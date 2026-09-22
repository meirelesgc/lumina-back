"""criar_tabela_branch_query_expansions

Revision ID: 3505c2db872a
Revises: 0009
Create Date: 2026-09-22 12:02:37.353829

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3505c2db872a'
down_revision: Union[str, Sequence[str], None] = '0009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('branch_query_expansions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('branch_id', sa.Uuid(), nullable=False),
        sa.Column('expansion_text', sa.String(), nullable=False),
        sa.Column('expansion_type', sa.String(), nullable=False),
        sa.Column('generation_model', sa.String(), nullable=False),
        sa.Column('generation_version', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.Uuid(), nullable=True),
        sa.Column('updated_by', sa.Uuid(), nullable=True),
        sa.Column('deleted_by', sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(['branch_id'], ['branches.id'], name='fk_branch_query_expansion_branch_id'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], name='fk_branch_query_expansions_created_by', use_alter=True),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], name='fk_branch_query_expansions_updated_by', use_alter=True),
        sa.ForeignKeyConstraint(['deleted_by'], ['users.id'], name='fk_branch_query_expansions_deleted_by', use_alter=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_branch_query_expansions_branch_active',
        'branch_query_expansions',
        ['branch_id', 'is_active'],
        unique=False,
        postgresql_where=sa.text('deleted_at IS NULL'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        'ix_branch_query_expansions_branch_active',
        table_name='branch_query_expansions',
        postgresql_where=sa.text('deleted_at IS NULL'),
    )
    op.drop_table('branch_query_expansions')
