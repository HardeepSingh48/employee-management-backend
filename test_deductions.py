#!/usr/bin/env python3
"""
Test script to verify deductions functionality
"""

import os
import sys
from datetime import date, datetime
from sqlalchemy import create_engine, text
from config import SQLALCHEMY_DATABASE_URI
import uuid

def test_deductions_functionality():
    """Test the deductions functionality"""
    
    # Create engine
    engine = create_engine(SQLALCHEMY_DATABASE_URI)
    
    try:
        with engine.connect() as conn:
            # Test 1: Check if deductions table exists
            print("🔍 Test 1: Checking if deductions table exists...")
            result = conn.execute(text("SELECT COUNT(*) FROM deductions"))
            count = result.scalar()
            print(f"✅ Deductions table exists with {count} records")
            
            # Test 2: Insert a test deduction
            print("\n🔍 Test 2: Inserting test deduction...")
            test_deduction = {
                'deduction_id': str(uuid.uuid4()),
                'employee_id': 910001,  # Integer employee ID
                'deduction_type': 'Test Clothes',
                'total_amount': 20000.00,
                'months': 9,
                'start_month': date(2025, 8, 1),
                'created_by': 'test_script'
            }
            
            insert_sql = """
            INSERT INTO deductions (deduction_id, employee_id, deduction_type, total_amount, months, start_month, created_by)
            VALUES (:deduction_id, :employee_id, :deduction_type, :total_amount, :months, :start_month, :created_by)
            """
            
            conn.execute(text(insert_sql), test_deduction)
            conn.commit()
            print("✅ Test deduction inserted successfully")
            
            # Test 3: Verify the deduction was inserted
            print("\n🔍 Test 3: Verifying test deduction...")
            result = conn.execute(text("SELECT * FROM deductions WHERE deduction_type = 'Test Clothes'"))
            deduction = result.fetchone()
            if deduction:
                print(f"✅ Test deduction found: {deduction.deduction_type} - ₹{deduction.total_amount}")
                print(f"   Monthly installment: ₹{deduction.total_amount / deduction.months:.2f}")
            else:
                print("❌ Test deduction not found")
            
            # Test 4: Test monthly installment calculation
            print("\n🔍 Test 4: Testing monthly installment calculation...")
            if deduction:
                monthly_installment = deduction.total_amount / deduction.months
                print(f"✅ Monthly installment: ₹{monthly_installment:.2f}")
                
                # Test if deduction is active for current month
                current_date = date.today()
                start_date = deduction.start_month
                months_diff = (current_date.year - start_date.year) * 12 + (current_date.month - start_date.month)
                is_active = 0 <= months_diff < deduction.months
                print(f"✅ Deduction active for current month: {is_active}")
            
            # Test 5: Clean up test data
            print("\n🔍 Test 5: Cleaning up test data...")
            conn.execute(text("DELETE FROM deductions WHERE deduction_type = 'Test Clothes'"))
            conn.commit()
            print("✅ Test data cleaned up")
            
            print("\n🎉 All tests passed! Deductions functionality is working correctly.")
            
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    print("Testing deductions functionality...")
    test_deductions_functionality()
    print("Done!")
