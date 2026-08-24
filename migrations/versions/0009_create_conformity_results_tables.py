"""create conformity results tables

Revision ID: 0009
Revises: 0008
Create Date: 2026-08-23 22:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0009'
down_revision: Union[str, Sequence[str], None] = '0008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'template_conformity_results',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('doc_id', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='processing'),
        sa.Column('file_path', sa.String(), nullable=False),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('report', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
            ['created_by'],
            ['users.id'],
            name='fk_template_conformity_results_created_by',
            use_alter=True,
        ),
        sa.ForeignKeyConstraint(
            ['deleted_by'],
            ['users.id'],
            name='fk_template_conformity_results_deleted_by',
            use_alter=True,
        ),
        sa.ForeignKeyConstraint(
            ['updated_by'],
            ['users.id'],
            name='fk_template_conformity_results_updated_by',
            use_alter=True,
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_template_conformity_results_doc_id',
        'template_conformity_results',
        ['doc_id'],
        unique=False,
    )
    op.create_index(
        'ix_template_conformity_doc_id_created_at',
        'template_conformity_results',
        ['doc_id', 'created_at'],
        unique=False,
    )

    op.create_table(
        'abnt_conformity_results',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('doc_id', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='processing'),
        sa.Column('file_path', sa.String(), nullable=False),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('report', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
            ['created_by'],
            ['users.id'],
            name='fk_abnt_conformity_results_created_by',
            use_alter=True,
        ),
        sa.ForeignKeyConstraint(
            ['deleted_by'],
            ['users.id'],
            name='fk_abnt_conformity_results_deleted_by',
            use_alter=True,
        ),
        sa.ForeignKeyConstraint(
            ['updated_by'],
            ['users.id'],
            name='fk_abnt_conformity_results_updated_by',
            use_alter=True,
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_abnt_conformity_results_doc_id',
        'abnt_conformity_results',
        ['doc_id'],
        unique=False,
    )
    op.create_index(
        'ix_abnt_conformity_doc_id_created_at',
        'abnt_conformity_results',
        ['doc_id', 'created_at'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        'ix_abnt_conformity_doc_id_created_at',
        table_name='abnt_conformity_results',
    )
    op.drop_index(
        'ix_abnt_conformity_results_doc_id',
        table_name='abnt_conformity_results',
    )
    op.drop_table('abnt_conformity_results')

    op.drop_index(
        'ix_template_conformity_doc_id_created_at',
        table_name='template_conformity_results',
    )
    op.drop_index(
        'ix_template_conformity_results_doc_id',
        table_name='template_conformity_results',
    )
    op.drop_table('template_conformity_results')
