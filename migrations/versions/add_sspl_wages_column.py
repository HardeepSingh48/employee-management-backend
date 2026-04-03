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
    # Add sspl_wages column conditionally
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name='wage_masters' AND column_name='sspl_wages'
            ) THEN
                ALTER TABLE wage_masters ADD COLUMN sspl_wages FLOAT;
            END IF;
        END
        $$;
    """)

def downgrade():
    # Remove sspl_wages column from wage_masters table
    op.drop_column('wage_masters', 'sspl_wages')