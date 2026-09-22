"""create_invitations_table

Revision ID: 2d024364c639
Revises: fa603197d76f
Create Date: 2026-09-22 18:45:50.512758

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '2d024364c639'
down_revision: Union[str, Sequence[str], None] = 'fa603197d76f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'invitations',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('inviter_id', sa.Uuid(), nullable=False),
        sa.Column('token', sa.String(length=128), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('project_id', sa.Uuid(), nullable=True),
        sa.Column('role_type', sa.String(), nullable=False),
        sa.Column('topic', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('accepted_at', sa.DateTime(), nullable=True),
        sa.Column('rejected_at', sa.DateTime(), nullable=True),
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
            name='fk_invitations_created_by',
            use_alter=True,
        ),
        sa.ForeignKeyConstraint(
            ['deleted_by'],
            ['users.id'],
            name='fk_invitations_deleted_by',
            use_alter=True,
        ),
        sa.ForeignKeyConstraint(
            ['inviter_id'],
            ['users.id'],
            name='fk_invitations_inviter_id',
        ),
        sa.ForeignKeyConstraint(
            ['project_id'],
            ['projects.id'],
            name='fk_invitations_project_id',
        ),
        sa.ForeignKeyConstraint(
            ['updated_by'],
            ['users.id'],
            name='fk_invitations_updated_by',
            use_alter=True,
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_invitations_email'), 'invitations', ['email'], unique=False
    )
    op.create_index(
        op.f('ix_invitations_token'), 'invitations', ['token'], unique=True
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_invitations_token'), table_name='invitations')
    op.drop_index(op.f('ix_invitations_email'), table_name='invitations')
    op.drop_table('invitations')
