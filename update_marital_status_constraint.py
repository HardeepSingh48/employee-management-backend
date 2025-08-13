#!/usr/bin/env python3
"""
Update marital status constraint to support all 4 options
"""

import os
import sys
from flask import Flask
from models import db
from sqlalchemy import text
from config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS, SECRET_KEY

def update_marital_status_constraint():
    """Update the marital status constraint to support all 4 options"""
    
    # Create Flask app for database operations
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS
    app.config["SECRET_KEY"] = SECRET_KEY
    
    db.init_app(app)
    
    with app.app_context():
        try:
            print("Updating marital status constraint...")

            # First, check what values currently exist
            result = db.session.execute(text("""
                SELECT DISTINCT marital_status FROM employees WHERE marital_status IS NOT NULL;
            """))
            existing_values = [row[0] for row in result.fetchall()]
            print(f"Existing marital status values: {existing_values}")

            # Drop the old constraint
            db.session.execute(text("""
                ALTER TABLE employees
                DROP CONSTRAINT IF EXISTS employees_marital_status_check;
            """))

            # Update existing data to match new format
            print("Updating existing data...")
            db.session.execute(text("""
                UPDATE employees
                SET marital_status = CASE
                    WHEN LOWER(marital_status) = 'unmarried' THEN 'Single'
                    WHEN LOWER(marital_status) = 'married' THEN 'Married'
                    WHEN LOWER(marital_status) = 'divorced' THEN 'Divorced'
                    WHEN LOWER(marital_status) = 'widowed' THEN 'Widowed'
                    WHEN LOWER(marital_status) = 'single' THEN 'Single'
                    ELSE marital_status
                END
                WHERE marital_status IS NOT NULL;
            """))

            # Add the new constraint with all 4 options
            db.session.execute(text("""
                ALTER TABLE employees
                ADD CONSTRAINT employees_marital_status_check
                CHECK (marital_status IN ('Single', 'Married', 'Divorced', 'Widowed'));
            """))

            db.session.commit()
            print("✅ Marital status constraint updated successfully!")
            print("Now supports: Single, Married, Divorced, Widowed")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error updating constraint: {e}")
            sys.exit(1)

if __name__ == "__main__":
    update_marital_status_constraint()
