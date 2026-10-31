"""remover_recuperacao_por_ramo

Revision ID: c4d1e7a92b36
Revises: 0adaecd70bea
Create Date: 2026-10-31 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4d1e7a92b36'
down_revision: Union[str, Sequence[str], None] = '0adaecd70bea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_index(
        'ix_branch_query_expansions_branch_active',
        table_name='branch_query_expansions',
        postgresql_where=sa.text('deleted_at IS NULL'),
    )
    op.drop_table('branch_query_expansions')
    op.drop_column('applied_branches', 'expansion_generation_version')

    # O PGVector cria esta tabela em tempo de execução, então uma base nova
    # chega aqui sem ela.
    op.execute(
        """
        DO $$
        BEGIN
            IF to_regclass('langchain_pg_embedding') IS NOT NULL THEN
                DELETE FROM langchain_pg_embedding
                WHERE cmetadata->>'record_type' = 'section_summary';
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        'applied_branches',
        sa.Column(
            'expansion_generation_version', sa.Integer(), nullable=True
        ),
    )
    op.create_table(
        'branch_query_expansions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('branch_id', sa.Uuid(), nullable=False),
        sa.Column('expansion_text', sa.String(), nullable=False),
        sa.Column('expansion_type', sa.String(), nullable=False),
        sa.Column('generation_model', sa.String(), nullable=False),
        sa.Column('generation_version', sa.Integer(), nullable=False),
        sa.Column(
            'is_active',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('true'),
        ),
        sa.Column(
            'created_at',
            sa.DateTime(),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.Uuid(), nullable=True),
        sa.Column('updated_by', sa.Uuid(), nullable=True),
        sa.Column('deleted_by', sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(
            ['branch_id'],
            ['branches.id'],
            name='fk_branch_query_expansion_branch_id',
        ),
        sa.ForeignKeyConstraint(
            ['created_by'],
            ['users.id'],
            name='fk_branch_query_expansions_created_by',
            use_alter=True,
        ),
        sa.ForeignKeyConstraint(
            ['updated_by'],
            ['users.id'],
            name='fk_branch_query_expansions_updated_by',
            use_alter=True,
        ),
        sa.ForeignKeyConstraint(
            ['deleted_by'],
            ['users.id'],
            name='fk_branch_query_expansions_deleted_by',
            use_alter=True,
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_branch_query_expansions_branch_active',
        'branch_query_expansions',
        ['branch_id', 'is_active'],
        unique=False,
        postgresql_where=sa.text('deleted_at IS NULL'),
    )
