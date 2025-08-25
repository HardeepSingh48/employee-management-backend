#!/usr/bin/env python3
"""
Script to add sample deductions for testing Form B
"""

import os
import sys
from datetime import date
from sqlalchemy import create_engine, text
from config import SQLALCHEMY_DATABASE_URI
import uuid

def add_sample_deductions():
    """Add sample deductions for testing"""
    
    # Create engine
    engine = create_engine(SQLALCHEMY_DATABASE_URI)
    
    try:
        with engine.connect() as conn:
            # First, check if we have any employees
            print("🔍 Checking available employees...")
            result = conn.execute(text("SELECT employee_id, first_name, last_name FROM employees LIMIT 5"))
            employees = result.fetchall()
            
            if not employees:
                print("❌ No employees found. Please add some employees first.")
                return
            
            print(f"✅ Found {len(employees)} employees:")
            for emp in employees:
                print(f"   - {emp.employee_id}: {emp.first_name} {emp.last_name}")
            
            # Add sample deductions for the first few employees
            sample_deductions = [
                {
                    'employee_id': employees[0].employee_id,
                    'deduction_type': 'Clothes',
                    'total_amount': 20000.00,
                    'months': 9,
                    'start_month': date(2024, 8, 1)
                },
                {
                    'employee_id': employees[0].employee_id,
                    'deduction_type': 'Loan',
                    'total_amount': 15000.00,
                    'months': 6,
                    'start_month': date(2024, 9, 1)
                }
            ]
            
            if len(employees) > 1:
                sample_deductions.append({
                    'employee_id': employees[1].employee_id,
                    'deduction_type': 'Recovery',
                    'total_amount': 12000.00,
                    'months': 4,
                    'start_month': date(2024, 10, 1)
                })
            
            # Insert sample deductions
            print(f"\n🔍 Adding {len(sample_deductions)} sample deductions...")
            
            for deduction in sample_deductions:
                deduction_id = str(uuid.uuid4())
                
                insert_sql = """
                INSERT INTO deductions (deduction_id, employee_id, deduction_type, total_amount, months, start_month, created_by)
                VALUES (:deduction_id, :employee_id, :deduction_type, :total_amount, :months, :start_month, :created_by)
                """
                
                conn.execute(text(insert_sql), {
                    'deduction_id': deduction_id,
                    'employee_id': deduction['employee_id'],
                    'deduction_type': deduction['deduction_type'],
                    'total_amount': deduction['total_amount'],
                    'months': deduction['months'],
                    'start_month': deduction['start_month'],
                    'created_by': 'sample_data'
                })
                
                monthly_installment = deduction['total_amount'] / deduction['months']
                print(f"   ✅ Added {deduction['deduction_type']} for employee {deduction['employee_id']}: ₹{deduction['total_amount']} over {deduction['months']} months (₹{monthly_installment:.2f}/month)")
            
            conn.commit()
            
            # Verify the deductions were added
            print(f"\n🔍 Verifying deductions...")
            result = conn.execute(text("SELECT COUNT(*) FROM deductions"))
            count = result.scalar()
            print(f"✅ Total deductions in database: {count}")
            
            # Show current active deductions for December 2024
            print(f"\n🔍 Active deductions for December 2024:")
            result = conn.execute(text("""
                SELECT d.employee_id, e.first_name, e.last_name, d.deduction_type, d.total_amount, d.months, d.start_month
                FROM deductions d
                JOIN employees e ON d.employee_id = e.employee_id
                WHERE d.start_month <= '2024-12-01' 
                AND DATE_ADD(d.start_month, INTERVAL d.months MONTH) > '2024-12-01'
            """))
            
            active_deductions = result.fetchall()
            if active_deductions:
                for deduction in active_deductions:
                    monthly_installment = deduction.total_amount / deduction.months
                    print(f"   - {deduction.employee_id} ({deduction.first_name} {deduction.last_name}): {deduction.deduction_type} ₹{monthly_installment:.2f}/month")
            else:
                print("   No active deductions for December 2024")
            
            print(f"\n🎉 Sample deductions added successfully!")
            print(f"💡 Now test Form B with December 2024 to see the deductions.")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    print("Adding sample deductions for testing...")
    add_sample_deductions()
    print("Done!")
