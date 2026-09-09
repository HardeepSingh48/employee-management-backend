"""Remove the stale attendance status constraint.

Revision ID: 20260906_fix_attendance_ck
Revises: 20260906_reliever_attendance
Create Date: 2026-09-06
"""

from alembic import op


revision = '20260906_fix_attendance_ck'
down_revision = '20260906_reliever_attendance'
branch_labels = None
depends_on = None


def upgrade():
    """Remove the legacy constraint that excludes Reliever status."""
    op.execute(
        "ALTER TABLE attendance "
        "DROP CONSTRAINT IF EXISTS attendance_attendance_status_check"
    )


def downgrade():
    """Restore the legacy constraint after removing Reliever records."""
    op.execute(
        "UPDATE attendance "
        "SET attendance_status = 'OFF' "
        "WHERE attendance_status = 'Reliever'"
    )
    op.execute(
        "ALTER TABLE attendance "
        "DROP CONSTRAINT IF EXISTS check_attendance_status"
    )
    op.execute(
        "ALTER TABLE attendance "
        "DROP CONSTRAINT IF EXISTS attendance_attendance_status_check"
    )
    op.create_check_constraint(
        'attendance_attendance_status_check',
        'attendance',
        "attendance_status IN ('Present', 'Absent', 'OFF')"
    )
