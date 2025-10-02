#!/usr/bin/env python3
"""
Simple script to add performance indexes to the employees table.
Run this directly: python add_indexes.py
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db

# Create the app without registering blueprints (for scripts)
app = create_app(register_blueprints=False)

def add_employee_indexes():
    """Add performance indexes to the employees table."""

    with app.app_context():
        try:
            print("Adding performance indexes to employees table...")

            # Create indexes using raw SQL
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_employee_phone_email ON employees (phone_number, email)",
                "CREATE INDEX IF NOT EXISTS idx_employee_phone ON employees (phone_number)",
                "CREATE INDEX IF NOT EXISTS idx_employee_email ON employees (email)",
                "CREATE INDEX IF NOT EXISTS idx_employee_adhar ON employees (adhar_number)",
                "CREATE INDEX IF NOT EXISTS idx_employee_pan ON employees (pan_card_number)",
                "CREATE INDEX IF NOT EXISTS idx_employee_name ON employees (first_name, last_name)",
                "CREATE INDEX IF NOT EXISTS idx_employee_department ON employees (department_id)",
                "CREATE INDEX IF NOT EXISTS idx_employee_status ON employees (employment_status)",
                "CREATE INDEX IF NOT EXISTS idx_employee_site ON employees (site_id)",
                "CREATE INDEX IF NOT EXISTS idx_employee_hire_date ON employees (hire_date)"
            ]

            for index_sql in indexes:
                print(f"Creating index: {index_sql.split(' ON ')[0]}")
                db.session.execute(db.text(index_sql))

            db.session.commit()
            print("✅ All indexes added successfully!")

        except Exception as e:
            db.session.rollback()
            print(f"❌ Error adding indexes: {e}")
            return False

    return True

def remove_employee_indexes():
    """Remove the added indexes (for rollback)."""

    with app.app_context():
        try:
            print("Removing performance indexes from employees table...")

            indexes = [
                "DROP INDEX IF EXISTS idx_employee_phone_email",
                "DROP INDEX IF EXISTS idx_employee_phone",
                "DROP INDEX IF EXISTS idx_employee_email",
                "DROP INDEX IF EXISTS idx_employee_adhar",
                "DROP INDEX IF EXISTS idx_employee_pan",
                "DROP INDEX IF EXISTS idx_employee_name",
                "DROP INDEX IF EXISTS idx_employee_department",
                "DROP INDEX IF EXISTS idx_employee_status",
                "DROP INDEX IF EXISTS idx_employee_site",
                "DROP INDEX IF EXISTS idx_employee_hire_date"
            ]

            for index_sql in indexes:
                print(f"Dropping index: {index_sql.split(' IF EXISTS ')[1]}")
                db.session.execute(db.text(index_sql))

            db.session.commit()
            print("✅ All indexes removed successfully!")

        except Exception as e:
            db.session.rollback()
            print(f"❌ Error removing indexes: {e}")
            return False

    return True

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "remove":
        print("Removing indexes...")
        remove_employee_indexes()
    else:
        print("Adding indexes...")
        add_employee_indexes()