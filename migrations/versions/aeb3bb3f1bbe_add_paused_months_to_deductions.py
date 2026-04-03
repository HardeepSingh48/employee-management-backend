"""Add paused_months to deductions

Revision ID: aeb3bb3f1bbe
Revises: c31f4ebd0cc7
Create Date: 2026-04-03 23:02:58.558238

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'aeb3bb3f1bbe'
down_revision = 'c31f4ebd0cc7'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                           WHERE table_name='deductions' AND column_name='paused_months') THEN
                ALTER TABLE deductions ADD COLUMN paused_months INTEGER DEFAULT 0 NOT NULL;
            END IF;
        END $$;
    """)

def downgrade():
    op.drop_column('deductions', 'paused_months')
