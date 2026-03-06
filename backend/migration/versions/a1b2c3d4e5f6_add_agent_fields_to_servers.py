"""add agent fields to servers

Revision ID: a1b2c3d4e5f6
Revises: bf0a31f81f0d
Create Date: 2026-02-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'bf0a31f81f0d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('servers', sa.Column('agent_url', sa.String(length=255), nullable=True))
    op.add_column('servers', sa.Column('agent_token', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('servers', 'agent_token')
    op.drop_column('servers', 'agent_url')