#!/usr/bin/env python3
"""
Script to create the deductions table in the database
"""

import os
import sys
from sqlalchemy import create_engine, text
from config import SQLALCHEMY_DATABASE_URI

def create_deductions_table():
    """Create the deductions table if it doesn't exist"""
    
    # Create engine
    engine = create_engine(SQLALCHEMY_DATABASE_URI)
    
    # SQL to create the deductions table
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS deductions (
        deduction_id VARCHAR(36) PRIMARY KEY,
        employee_id INTEGER NOT NULL,
        deduction_type VARCHAR(100) NOT NULL,
        total_amount DECIMAL(10,2) NOT NULL,
        months INTEGER NOT NULL,
        start_month DATE NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE,
        created_by VARCHAR(100),
        updated_by VARCHAR(100),
        FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
    );
    """
    
    try:
        with engine.connect() as conn:
            # Create the table
            conn.execute(text(create_table_sql))
            conn.commit()
            print("✅ Deductions table created successfully!")
            
            # Verify the table exists
            result = conn.execute(text("SELECT COUNT(*) FROM deductions"))
            count = result.scalar()
            print(f"✅ Table verification: {count} records found in deductions table")
            
    except Exception as e:
        print(f"❌ Error creating deductions table: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    print("Creating deductions table...")
    create_deductions_table()
    print("Done!")
