#!/usr/bin/env python3
"""
Debug script to test Form B deductions integration
"""

import os
import sys
from datetime import date
from sqlalchemy import create_engine, text
from config import SQLALCHEMY_DATABASE_URI

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.salary_service import SalaryService
from models.employee import Employee
from models import db
from app import create_app

def debug_form_b():
    """Debug Form B deductions"""
    
    # Create Flask app context
    app = create_app(register_blueprints=False)
    
    with app.app_context():
        try:
            print("🔍 Testing Form B deductions integration...")
            
            # Get first employee
            employee = Employee.query.first()
            if not employee:
                print("❌ No employees found")
                return
            
            print(f"✅ Testing with employee: {employee.employee_id} - {employee.first_name} {employee.last_name}")
            
            # Test get_monthly_deductions method
            year = 2024
            month = 12
            
            print(f"🔍 Getting deductions for {month}/{year}...")
            total_deduction, deduction_details = SalaryService.get_monthly_deductions(
                employee.employee_id, year, month
            )
            
            print(f"✅ Total deduction: {total_deduction} (type: {type(total_deduction)})")
            print(f"✅ Deduction details: {deduction_details}")
            
            # Test individual salary calculation
            print(f"\n🔍 Testing individual salary calculation...")
            salary_result = SalaryService.calculate_individual_salary(
                employee.employee_id, year, month
            )
            
            if salary_result['success']:
                salary_data = salary_result['data']
                print(f"✅ Salary calculation successful")
                print(f"   - Total Deductions: {salary_data.get('Total Deductions', 'N/A')}")
                print(f"   - Net Salary: {salary_data.get('Net Salary', 'N/A')}")
                
                # Check for dynamic deduction fields
                dynamic_deductions = {}
                for key, value in salary_data.items():
                    if key not in ['Employee ID', 'Employee Name', 'Skill Level', 'Present Days', 'Daily Wage', 
                                   'Basic', 'Special Basic', 'DA', 'HRA', 'Overtime', 'Others', 'Total Earnings',
                                   'PF', 'ESIC', 'Society', 'Income Tax', 'Insurance', 'Others Recoveries',
                                   'Total Deductions', 'Net Salary'] and isinstance(value, (int, float)) and value > 0:
                        dynamic_deductions[key] = value
                
                if dynamic_deductions:
                    print(f"   - Dynamic deductions found: {dynamic_deductions}")
                else:
                    print(f"   - No dynamic deductions found")
            else:
                print(f"❌ Salary calculation failed: {salary_result.get('message', 'Unknown error')}")
            
            print(f"\n🎉 Debug completed!")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    print("Debugging Form B deductions...")
    debug_form_b()
    print("Done!")
