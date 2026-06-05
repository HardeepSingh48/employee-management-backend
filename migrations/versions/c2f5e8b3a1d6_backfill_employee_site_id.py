"""backfill_employee_site_id

Backfills employees.site_id by joining via salary_code -> wage_masters -> site_id.

Revision ID: c2f5e8b3a1d6
Revises: b1e4f7a2c9d3
Create Date: 2026-06-06
"""
from alembic import op
import sqlalchemy as sa

revision = 'c2f5e8b3a1d6'
down_revision = 'b1e4f7a2c9d3'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()

    # Backfill employees.site_id via their salary_code -> wage_masters.site_id
    result = connection.execute(sa.text("""
        UPDATE employees
        SET site_id = wm.site_id
        FROM wage_masters wm
        WHERE employees.salary_code = wm.salary_code
          AND wm.site_id IS NOT NULL
          AND employees.site_id IS NULL
    """))

    # Report how many were updated (Alembic doesn't expose rowcount easily, but the migration will succeed)


def downgrade():
    connection = op.get_bind()
    # Nullify the backfilled site_ids (we can't distinguish auto-filled vs manually set, so we clear all)
    connection.execute(sa.text("UPDATE employees SET site_id = NULL"))
