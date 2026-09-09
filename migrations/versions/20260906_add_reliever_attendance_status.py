"""Add support for reliever-duty attendance.

Revision ID: 20260906_reliever_attendance
Revises: c2f5e8b3a1d6
Create Date: 2026-09-06
"""

from alembic import op


revision = '20260906_reliever_attendance'
down_revision = 'c2f5e8b3a1d6'
branch_labels = None
depends_on = None


def upgrade():
    # Normalize any legacy values before tightening the constraint.
    op.execute(
        """
        UPDATE attendance
        SET attendance_status = 'Reliever'
        WHERE upper(trim(attendance_status)) IN ('R', 'RELIEVER', 'RELIEVER DUTY')
        """
    )
    op.execute(
        """
        UPDATE attendance
        SET attendance_status = 'Absent'
        WHERE attendance_status NOT IN ('Present', 'Absent', 'OFF', 'Reliever')
        """
    )

    # Older databases may have the SQLAlchemy-generated constraint name,
    # while newer migration-created schemas use the explicit name below.
    op.execute("ALTER TABLE attendance DROP CONSTRAINT IF EXISTS check_attendance_status")
    op.execute("ALTER TABLE attendance DROP CONSTRAINT IF EXISTS attendance_attendance_status_check")
    op.create_check_constraint(
        'check_attendance_status',
        'attendance',
        "attendance_status IN ('Present', 'Absent', 'OFF', 'Reliever')"
    )


def downgrade():
    # Reliever is not representable in the previous schema; preserve the row
    # while reverting it to the neutral non-working status.
    op.execute(
        "UPDATE attendance SET attendance_status = 'OFF' WHERE attendance_status = 'Reliever'"
    )
    op.execute("ALTER TABLE attendance DROP CONSTRAINT IF EXISTS check_attendance_status")
    op.execute("ALTER TABLE attendance DROP CONSTRAINT IF EXISTS attendance_attendance_status_check")
    op.create_check_constraint(
        'check_attendance_status',
        'attendance',
        "attendance_status IN ('Present', 'Absent', 'OFF')"
    )
