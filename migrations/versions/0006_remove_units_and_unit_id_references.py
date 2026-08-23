"""remove units and unit_id references

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-18 23:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0006'
down_revision: Union[str, None] = 'e93940cdeacb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Remover FK e coluna unit_id de users
    conn = op.get_bind()
    conn.execute(sa.text("ALTER TABLE users DROP CONSTRAINT IF EXISTS fk_user_unit_id CASCADE"))
    conn.execute(sa.text("ALTER TABLE users DROP COLUMN IF EXISTS unit_id CASCADE"))

    # 2. Remover FKs e coluna unit_id de documents
    conn.execute(sa.text("ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_unit_id_fkey CASCADE"))
    conn.execute(sa.text("ALTER TABLE documents DROP COLUMN IF EXISTS unit_id CASCADE"))

    # 3. Remover indices e tabela units
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_units_tsv CASCADE"))
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_uq_units_name_active CASCADE"))
    conn.execute(sa.text("DROP TABLE IF EXISTS units CASCADE"))


def downgrade() -> None:
    op.create_table(
        'units',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('location', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.Uuid(), nullable=True),
        sa.Column('updated_by', sa.Uuid(), nullable=True),
        sa.Column('deleted_by', sa.Uuid(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.add_column('users', sa.Column('unit_id', sa.Uuid(), nullable=True))
    op.create_foreign_key('fk_user_unit_id', 'users', 'units', ['unit_id'], ['id'])

    op.add_column('documents', sa.Column('unit_id', sa.Uuid(), nullable=True))
    op.create_foreign_key('documents_unit_id_fkey', 'documents', 'units', ['unit_id'], ['id'])
