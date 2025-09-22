"""Add attendance performance indexes

Revision ID: add_attendance_indexes
Revises: [your_previous_revision]
Create Date: 2025-01-XX XX:XX:XX.XXXXXX

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'add_attendance_indexes'
down_revision = None  # Replace with your latest migration revision
branch_labels = None
depends_on = None


def upgrade():
    """Add indexes for better attendance query performance"""
    
    # Most important index: composite index for employee_id + attendance_date lookups
    # This will dramatically speed up the bulk loading of existing attendance
    op.create_index(
        'idx_attendance_employee_date', 
        'attendance', 
        ['employee_id', 'attendance_date'],
        if_not_exists=True
    )
    
    # Index for date-based queries (reports, monthly summaries)
    op.create_index(
        'idx_attendance_date', 
        'attendance', 
        ['attendance_date'],
        if_not_exists=True
    )
    
    # Index for employee-based queries
    op.create_index(
        'idx_attendance_employee', 
        'attendance', 
        ['employee_id'],
        if_not_exists=True
    )
    
    # Index for supervisor site-based filtering
    op.create_index(
        'idx_employee_site_id', 
        'employees',  # Adjust table name if different
        ['site_id', 'employee_id'],
        if_not_exists=True
    )
    
    # Index for employee_id lookups (if not already indexed)
    op.create_index(
        'idx_employee_employee_id', 
        'employees', 
        ['employee_id'],
        if_not_exists=True
    )
    
    # Optional: Index for attendance status queries
    op.create_index(
        'idx_attendance_status', 
        'attendance', 
        ['attendance_status'],
        if_not_exists=True
    )
    
    # Optional: Index for marked_by queries (if you filter by this)
    op.create_index(
        'idx_attendance_marked_by', 
        'attendance', 
        ['marked_by'],
        if_not_exists=True
    )


def downgrade():
    """Remove the indexes if needed"""
    
    # Drop indexes in reverse order
    op.drop_index('idx_attendance_marked_by', 'attendance', if_exists=True)
    op.drop_index('idx_attendance_status', 'attendance', if_exists=True)
    op.drop_index('idx_employee_employee_id', 'employees', if_exists=True)
    op.drop_index('idx_employee_site_id', 'employees', if_exists=True)
    op.drop_index('idx_attendance_employee', 'attendance', if_exists=True)
    op.drop_index('idx_attendance_date', 'attendance', if_exists=True)
    op.drop_index('idx_attendance_employee_date', 'attendance', if_exists=True)