"""Add soft delete columns to employees table

Revision ID: a1b2c3d4e5f6
Revises: f6a2b3c4d5e6
Create Date: 2026-04-02 00:48:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'f6a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade():
    # Add soft delete columns to the employees table
    with op.batch_alter_table('employees', schema=None) as batch_op:
        batch_op.add_column(sa.Column(
            'is_deleted',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false')
        ))
        batch_op.add_column(sa.Column(
            'deleted_at',
            sa.DateTime(timezone=True),
            nullable=True
        ))
        batch_op.add_column(sa.Column(
            'left_on',
            sa.Date(),
            nullable=True
        ))


def downgrade():
    with op.batch_alter_table('employees', schema=None) as batch_op:
        batch_op.drop_column('left_on')
        batch_op.drop_column('deleted_at')
        batch_op.drop_column('is_deleted')
