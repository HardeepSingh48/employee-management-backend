"""Merge multiple migration heads

Revision ID: c31f4ebd0cc7
Revises: add_username_field, b2c3d4e5f6a7
Create Date: 2026-04-03 21:29:21.328244

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c31f4ebd0cc7'
down_revision = ('add_username_field', 'b2c3d4e5f6a7')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
