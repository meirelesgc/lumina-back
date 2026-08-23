"""merge publication_templates and advisorships heads

Revision ID: 0008
Revises: 370ce92b8009, 0007
Create Date: 2026-08-23 12:10:00.000000

"""
from typing import Sequence, Union


revision: str = '0008'
down_revision: Union[str, Sequence[str], None] = ('370ce92b8009', '0007')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
