"""add started_at to access_keys

Revision ID: c1d2e3f4a5b6
Revises: 28600d1d50c4
Create Date: 2026-03-29 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, Sequence[str], None] = '28600d1d50c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('access_keys', sa.Column('started_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('access_keys', 'started_at')