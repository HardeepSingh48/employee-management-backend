"""add username field to users table

Revision ID: add_username_field
Revises: add_sspl_wages
Create Date: 2025-11-22 15:05:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_username_field'
down_revision = 'add_sspl_wages'
branch_labels = None
depends_on = None


def upgrade():
    # Add username column to users table
    op.add_column('users', sa.Column('username', sa.String(length=80), nullable=True))
    # Create unique index for username
    op.create_index('ix_users_username', 'users', ['username'], unique=True)


def downgrade():
    # Drop the unique index
    op.drop_index('ix_users_username', table_name='users')
    # Remove username column from users table
    op.drop_column('users', 'username')