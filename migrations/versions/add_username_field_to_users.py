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
    # Add username column conditionally
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name='users' AND column_name='username'
            ) THEN
                ALTER TABLE users ADD COLUMN username VARCHAR(80);
            END IF;
        END
        $$;
    """)
    # Create unique index for username conditionally
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_indexes
                WHERE indexname = 'ix_users_username'
            ) THEN
                CREATE UNIQUE INDEX ix_users_username ON users (username);
            END IF;
        END
        $$;
    """)

def downgrade():
    # Drop the unique index
    op.drop_index('ix_users_username', table_name='users')
    # Remove username column from users table
    op.drop_column('users', 'username')