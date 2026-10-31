"""remover_kanban

Revision ID: c4f1a7e29b3d
Revises: 0adaecd70bea
Create Date: 2026-10-31 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4f1a7e29b3d'
down_revision: Union[str, Sequence[str], None] = '0adaecd70bea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'document_releases',
        sa.Column('document_id', sa.Uuid(), nullable=True),
    )
    op.execute(
        """
        UPDATE document_releases AS r
        SET document_id = h.document_id
        FROM document_histories AS h
        WHERE h.id = r.history_id
        """
    )
    op.alter_column('document_releases', 'document_id', nullable=False)
    op.create_foreign_key(
        'fk_document_releases_document_id',
        'document_releases',
        'documents',
        ['document_id'],
        ['id'],
    )
    op.create_index(
        'ix_document_releases_document_id',
        'document_releases',
        ['document_id'],
    )
    op.drop_constraint(
        'fk_document_releases_history_id',
        'document_releases',
        type_='foreignkey',
    )
    op.drop_column('document_releases', 'history_id')
    op.drop_table('document_histories')

    op.drop_column('project_documents', 'status')
    op.drop_column('project_documents', 'sent_to_kanban')

    op.execute(
        """
        UPDATE users
        SET access_level = 'DEFAULT'
        WHERE access_level IN ('AUDITOR', 'ANALYST')
        """
    )


def downgrade() -> None:
    """Downgrade schema.

    Recria a estrutura, sem recuperar a sequência de status antiga nem os
    níveis AUDITOR e ANALYST.
    """
    op.add_column(
        'project_documents',
        sa.Column(
            'sent_to_kanban',
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        'project_documents',
        sa.Column(
            'status',
            sa.String(),
            nullable=False,
            server_default='PENDING',
        ),
    )

    op.create_table(
        'document_histories',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('document_id', sa.Uuid(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
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
            name='fk_document_histories_created_by',
        ),
        sa.ForeignKeyConstraint(
            ['deleted_by'],
            ['users.id'],
            name='fk_document_histories_deleted_by',
        ),
        sa.ForeignKeyConstraint(
            ['document_id'],
            ['documents.id'],
            name='fk_document_histories_document_id',
        ),
        sa.ForeignKeyConstraint(
            ['updated_by'],
            ['users.id'],
            name='fk_document_histories_updated_by',
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.execute(
        """
        INSERT INTO document_histories
            (id, document_id, status, created_at, created_by)
        SELECT gen_random_uuid(), id, 'PENDING', created_at, created_by
        FROM documents
        """
    )
    op.add_column(
        'document_releases',
        sa.Column('history_id', sa.Uuid(), nullable=True),
    )
    op.execute(
        """
        UPDATE document_releases AS r
        SET history_id = h.id
        FROM document_histories AS h
        WHERE h.document_id = r.document_id
        """
    )
    op.alter_column('document_releases', 'history_id', nullable=False)
    op.create_foreign_key(
        'fk_document_releases_history_id',
        'document_releases',
        'document_histories',
        ['history_id'],
        ['id'],
    )
    op.drop_index(
        'ix_document_releases_document_id',
        table_name='document_releases',
    )
    op.drop_constraint(
        'fk_document_releases_document_id',
        'document_releases',
        type_='foreignkey',
    )
    op.drop_column('document_releases', 'document_id')
