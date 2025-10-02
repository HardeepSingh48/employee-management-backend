"""
Migration script to add performance indexes to the employees table.
Run this after updating the Employee model with the new indexes.
"""

from alembic import op
import sqlalchemy as sa

def upgrade():
    """Add indexes to employees table for better performance during bulk operations."""

    # Composite index for bulk lookups
    op.create_index('idx_employee_phone_email', 'employees', ['phone_number', 'email'])

    # Individual indexes for search operations
    op.create_index('idx_employee_phone', 'employees', ['phone_number'])
    op.create_index('idx_employee_email', 'employees', ['email'])
    op.create_index('idx_employee_adhar', 'employees', ['adhar_number'])
    op.create_index('idx_employee_pan', 'employees', ['pan_card_number'])
    op.create_index('idx_employee_name', 'employees', ['first_name', 'last_name'])
    op.create_index('idx_employee_department', 'employees', ['department_id'])
    op.create_index('idx_employee_status', 'employees', ['employment_status'])
    op.create_index('idx_employee_site', 'employees', ['site_id'])

    # For date range queries
    op.create_index('idx_employee_hire_date', 'employees', ['hire_date'])

def downgrade():
    """Remove the added indexes."""

    op.drop_index('idx_employee_phone_email', 'employees')
    op.drop_index('idx_employee_phone', 'employees')
    op.drop_index('idx_employee_email', 'employees')
    op.drop_index('idx_employee_adhar', 'employees')
    op.drop_index('idx_employee_pan', 'employees')
    op.drop_index('idx_employee_name', 'employees')
    op.drop_index('idx_employee_department', 'employees')
    op.drop_index('idx_employee_status', 'employees')
    op.drop_index('idx_employee_site', 'employees')
    op.drop_index('idx_employee_hire_date', 'employees')