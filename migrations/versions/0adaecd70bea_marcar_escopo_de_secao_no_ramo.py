"""marcar_escopo_de_secao_no_ramo

Revision ID: 0adaecd70bea
Revises: ad86bd43da06
Create Date: 2026-10-29 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0adaecd70bea'
down_revision: Union[str, Sequence[str], None] = 'ad86bd43da06'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'branches',
        sa.Column(
            'section_scope',
            sa.String(),
            nullable=False,
            server_default='UNKNOWN',
        ),
    )
    op.add_column(
        'branches', sa.Column('expected_section', sa.String(), nullable=True)
    )
    op.drop_column('applied_branches', 'section_requirement_version')
    op.drop_index(
        'ix_branch_section_requirements_branch_active',
        table_name='branch_section_requirements',
        postgresql_where=sa.text('deleted_at IS NULL'),
    )
    op.drop_table('branch_section_requirements')


def downgrade() -> None:
    """Downgrade schema. As classificações apagadas não voltam."""
    op.create_table('branch_section_requirements',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('branch_id', sa.Uuid(), nullable=False),
        sa.Column('scope', sa.String(), nullable=False),
        sa.Column('expected_section', sa.String(), nullable=True),
        sa.Column('reasoning', sa.String(), nullable=True),
        sa.Column('generation_model', sa.String(), nullable=False),
        sa.Column('generation_version', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.Uuid(), nullable=True),
        sa.Column('updated_by', sa.Uuid(), nullable=True),
        sa.Column('deleted_by', sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(['branch_id'], ['branches.id'], name='fk_branch_section_requirement_branch_id'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], name='fk_branch_section_requirements_created_by', use_alter=True),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], name='fk_branch_section_requirements_updated_by', use_alter=True),
        sa.ForeignKeyConstraint(['deleted_by'], ['users.id'], name='fk_branch_section_requirements_deleted_by', use_alter=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_branch_section_requirements_branch_active',
        'branch_section_requirements',
        ['branch_id', 'is_active'],
        unique=False,
        postgresql_where=sa.text('deleted_at IS NULL'),
    )
    op.add_column(
        'applied_branches',
        sa.Column(
            'section_requirement_version', sa.Integer(), nullable=True
        ),
    )
    op.drop_column('branches', 'expected_section')
    op.drop_column('branches', 'section_scope')
