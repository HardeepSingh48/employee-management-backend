"""overtime_shifts to Float with default 0.0

Revision ID: 526657159ae9
Revises: 9d25b2d4dd3e
Create Date: 2025-08-28 14:04:15.629603
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '526657159ae9'
down_revision = '9d25b2d4dd3e'
branch_labels = None
depends_on = None


def upgrade():
    # Step 1: Add new column as nullable first
    with op.batch_alter_table('attendance', schema=None) as batch_op:
        batch_op.add_column(sa.Column('overtime_shifts', sa.Float(), nullable=True))

    # Step 2: Fill existing rows with 0.0
    op.execute("UPDATE attendance SET overtime_shifts = 0.0 WHERE overtime_shifts IS NULL;")

    # Step 3: Make column NOT NULL
    with op.batch_alter_table('attendance', schema=None) as batch_op:
        batch_op.alter_column('overtime_shifts', nullable=False)
        batch_op.drop_column('overtime_hours')


def downgrade():
    # Restore previous state
    with op.batch_alter_table('attendance', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('overtime_hours', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True)
        )
        batch_op.drop_column('overtime_shifts')
