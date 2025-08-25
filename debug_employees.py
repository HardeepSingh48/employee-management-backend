#!/usr/bin/env python3
"""
Debug script to check employee data structure
"""

import os
import sys
from sqlalchemy import create_engine, text
from config import SQLALCHEMY_DATABASE_URI

def debug_employees():
    """Debug employee data structure"""
    
    # Create engine
    engine = create_engine(SQLALCHEMY_DATABASE_URI)
    
    try:
        with engine.connect() as conn:
            # Check employees table structure
            print("🔍 Checking employees table structure...")
            result = conn.execute(text("SELECT * FROM employees LIMIT 3"))
            employees = result.fetchall()
            
            if employees:
                print(f"✅ Found {len(employees)} employees")
                for emp in employees:
                    print(f"   Employee ID: {emp.employee_id} (type: {type(emp.employee_id)})")
                    print(f"   Name: {emp.first_name} {emp.last_name}")
                    print(f"   Email: {emp.email}")
                    print("   ---")
            else:
                print("❌ No employees found")
                
            # Check table schema
            print("\n🔍 Checking employees table schema...")
            result = conn.execute(text("DESCRIBE employees"))
            schema = result.fetchall()
            for column in schema:
                if 'employee_id' in str(column).lower():
                    print(f"   employee_id column: {column}")
                    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    print("Debugging employees data structure...")
    debug_employees()
    print("Done!")
