"""add sspl_wages column to wage_masters table

Revision ID: add_sspl_wages
Revises: f6a2b3c4d5e6
Create Date: 2025-10-27 18:06:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_sspl_wages'
down_revision = 'f6a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade():
    # Add sspl_wages column to wage_masters table
    op.add_column('wage_masters', sa.Column('sspl_wages', sa.Float(), nullable=True))


def downgrade():
    # Remove sspl_wages column from wage_masters table
    op.drop_column('wage_masters', 'sspl_wages')