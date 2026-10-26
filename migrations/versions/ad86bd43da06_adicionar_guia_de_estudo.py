"""adicionar_guia_de_estudo

Revision ID: ad86bd43da06
Revises: 0211df046da3
Create Date: 2026-10-26 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'ad86bd43da06'
down_revision: Union[str, Sequence[str], None] = '0211df046da3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _audit_columns() -> list[sa.Column]:
    return [
        sa.Column(
            'created_at',
            sa.DateTime(),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column(
            'created_by',
            sa.Uuid(),
            sa.ForeignKey('users.id', name='fk_study_attachments_created_by'),
            nullable=True,
        ),
        sa.Column(
            'updated_by',
            sa.Uuid(),
            sa.ForeignKey('users.id', name='fk_study_attachments_updated_by'),
            nullable=True,
        ),
        sa.Column(
            'deleted_by',
            sa.Uuid(),
            sa.ForeignKey('users.id', name='fk_study_attachments_deleted_by'),
            nullable=True,
        ),
    ]


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'document_group_items',
        sa.Column('position', sa.Integer(), nullable=True),
    )
    op.execute(
        """
        UPDATE document_group_items AS i
        SET position = ranked.position
        FROM (
            SELECT id, row_number() OVER (
                PARTITION BY group_id ORDER BY created_at, id
            ) AS position
            FROM document_group_items
            WHERE deleted_at IS NULL
        ) AS ranked
        WHERE i.id = ranked.id
        """
    )
    op.execute(
        'UPDATE document_group_items SET position = 0 WHERE position IS NULL'
    )
    op.alter_column('document_group_items', 'position', nullable=False)

    op.create_table(
        'study_attachments',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('document_group_item_id', sa.Uuid(), nullable=False),
        sa.Column('kind', sa.String(length=20), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('typification_id', sa.Uuid(), nullable=True),
        sa.Column('doi', sa.String(), nullable=True),
        sa.Column(
            'authors', postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column('year', sa.Integer(), nullable=True),
        sa.Column('container_title', sa.String(), nullable=True),
        sa.Column('metadata_source', sa.String(length=20), nullable=True),
        sa.Column('url', sa.String(), nullable=True),
        *_audit_columns(),
        sa.ForeignKeyConstraint(
            ['document_group_item_id'],
            ['document_group_items.id'],
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(['typification_id'], ['typifications.id']),
        sa.CheckConstraint(
            "kind IN ('TYPIFICATION', 'DOI', 'LINK')",
            name='ck_study_attachments_kind',
        ),
        sa.CheckConstraint(
            "kind <> 'TYPIFICATION' OR typification_id IS NOT NULL",
            name='ck_study_attachments_typification',
        ),
        sa.CheckConstraint(
            "kind <> 'DOI' OR (doi IS NOT NULL AND metadata_source IS NOT NULL)",
            name='ck_study_attachments_doi',
        ),
        sa.CheckConstraint(
            "kind <> 'LINK' OR (url IS NOT NULL AND title IS NOT NULL)",
            name='ck_study_attachments_link',
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_uq_study_attachments_item_typification',
        'study_attachments',
        ['document_group_item_id', 'typification_id'],
        unique=True,
        postgresql_where=sa.text(
            'deleted_at IS NULL AND typification_id IS NOT NULL'
        ),
    )
    op.create_index(
        'ix_uq_study_attachments_item_doi',
        'study_attachments',
        ['document_group_item_id', 'doi'],
        unique=True,
        postgresql_where=sa.text('deleted_at IS NULL AND doi IS NOT NULL'),
    )
    op.create_index(
        'ix_uq_study_attachments_item_url',
        'study_attachments',
        ['document_group_item_id', 'url'],
        unique=True,
        postgresql_where=sa.text('deleted_at IS NULL AND url IS NOT NULL'),
    )

    op.create_table(
        'study_progress',
        sa.Column('project_id', sa.Uuid(), nullable=False),
        sa.Column('study_attachment_id', sa.Uuid(), nullable=False),
        sa.Column('studied_by', sa.Uuid(), nullable=False),
        sa.Column(
            'studied_at',
            sa.DateTime(),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['project_id'], ['projects.id'], ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['study_attachment_id'],
            ['study_attachments.id'],
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(['studied_by'], ['users.id']),
        sa.PrimaryKeyConstraint('project_id', 'study_attachment_id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('study_progress')
    op.drop_index(
        'ix_uq_study_attachments_item_url', table_name='study_attachments'
    )
    op.drop_index(
        'ix_uq_study_attachments_item_doi', table_name='study_attachments'
    )
    op.drop_index(
        'ix_uq_study_attachments_item_typification',
        table_name='study_attachments',
    )
    op.drop_table('study_attachments')
    op.drop_column('document_group_items', 'position')
