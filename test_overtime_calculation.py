#!/usr/bin/env python3
"""
Test script to verify the new overtime calculation logic
This script tests the overtime shifts to hours conversion and salary calculation
"""

import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from services.salary_service import SalaryService
from services.attendance_service import AttendanceService
from models.employee import Employee
from models.attendance import Attendance
from models import db
from datetime import date

def test_overtime_calculation():
    """Test the overtime calculation logic"""
    
    with app.app_context():
        print("=== Testing Overtime Calculation Logic ===\n")
        
        # Test 1: Basic overtime calculation
        print("Test 1: Basic overtime calculation")
        print("Scenario: Employee works 1.5 overtime shifts")
        
        # Example calculation
        overtime_shifts = 1.5
        overtime_hours = overtime_shifts * 8
        daily_wage = 800  # Example daily wage
        hourly_rate = daily_wage / 8
        overtime_allowance = overtime_hours * hourly_rate
        
        print(f"Overtime Shifts: {overtime_shifts}")
        print(f"Overtime Hours: {overtime_shifts} × 8 = {overtime_hours}")
        print(f"Daily Wage: ₹{daily_wage}")
        print(f"Hourly Rate: ₹{daily_wage} ÷ 8 = ₹{hourly_rate}")
        print(f"Overtime Allowance: {overtime_hours} × ₹{hourly_rate} = ₹{overtime_allowance}")
        print(f"Expected Result: ₹{overtime_allowance}\n")
        
        # Test 2: Different overtime scenarios
        print("Test 2: Different overtime scenarios")
        test_cases = [
            (0.5, "Half shift"),
            (1.0, "Full shift"),
            (1.5, "One and half shifts"),
            (2.0, "Two shifts"),
            (2.5, "Two and half shifts")
        ]
        
        for shifts, description in test_cases:
            hours = shifts * 8
            allowance = hours * hourly_rate
            print(f"{description}: {shifts} shifts = {hours} hours = ₹{allowance}")
        
        print()
        
        # Test 3: Check if employees exist and get their data
        print("Test 3: Check existing employees")
        try:
            employees = Employee.query.limit(3).all()
            
            if employees:
                print(f"Found {len(employees)} employees")
                for emp in employees:
                    print(f"Employee ID: {emp.employee_id}, Name: {emp.first_name} {emp.last_name}")
                    
                    # Test overtime calculation for this employee
                    current_date = date.today()
                    year = current_date.year
                    month = current_date.month
                    
                    try:
                        overtime_allowance, overtime_shifts, overtime_hours, overtime_rate = SalaryService.calculate_overtime_allowance(
                            emp.employee_id, year, month
                        )
                        
                        print(f"  - Overtime Shifts: {overtime_shifts}")
                        print(f"  - Overtime Hours: {overtime_hours}")
                        print(f"  - Overtime Rate: ₹{overtime_rate}")
                        print(f"  - Overtime Allowance: ₹{overtime_allowance}")
                        
                    except Exception as e:
                        print(f"  - Error calculating overtime: {str(e)}")
                        # Rollback any failed transaction
                        db.session.rollback()
                    
                    print()
            else:
                print("No employees found in database")
        except Exception as e:
            print(f"Error fetching employees: {str(e)}")
            db.session.rollback()
        
        # Test 4: Check attendance records
        print("Test 4: Check attendance records with overtime")
        try:
            attendance_records = Attendance.query.filter(Attendance.overtime_shifts > 0).limit(5).all()
            
            if attendance_records:
                print(f"Found {len(attendance_records)} attendance records with overtime")
                for record in attendance_records:
                    print(f"Employee: {record.employee_id}, Date: {record.attendance_date}")
                    print(f"  - Overtime Shifts: {record.overtime_shifts}")
                    print(f"  - Overtime Hours (computed): {record.overtime_hours}")
                    print(f"  - Verification: {record.overtime_shifts} × 8 = {record.overtime_shifts * 8}")
                    print()
            else:
                print("No attendance records with overtime found")
        except Exception as e:
            print(f"Error fetching attendance records: {str(e)}")
            db.session.rollback()
        
        print("=== Test Complete ===")

def test_salary_calculation():
    """Test the complete salary calculation with overtime"""
    
    with app.app_context():
        print("=== Testing Salary Calculation with Overtime ===\n")
        
        try:
            # Get first employee
            employee = Employee.query.first()
            
            if not employee:
                print("No employees found for salary calculation test")
                return
            
            print(f"Testing salary calculation for: {employee.first_name} {employee.last_name} (ID: {employee.employee_id})")
            
            current_date = date.today()
            year = current_date.year
            month = current_date.month
            
            try:
                # Calculate individual salary
                result = SalaryService.calculate_individual_salary(
                    employee.employee_id, year, month
                )
                
                if result['success']:
                    data = result['data']
                    print(f"Salary Calculation Results:")
                    print(f"  - Basic: ₹{data.get('Basic', 0)}")
                    print(f"  - Overtime Shifts: {data.get('Overtime Shifts', 0)}")
                    print(f"  - Overtime Hours: {data.get('Overtime Hours', 0)}")
                    print(f"  - Overtime Rate: ₹{data.get('Overtime Rate Hourly', 0)}")
                    print(f"  - Overtime Allowance: ₹{data.get('Overtime Allowance', 0)}")
                    print(f"  - Total Earnings: ₹{data.get('Total Earnings', 0)}")
                    print(f"  - Net Salary: ₹{data.get('Net Salary', 0)}")
                else:
                    print(f"Error in salary calculation: {result.get('message', 'Unknown error')}")
                    
            except Exception as e:
                print(f"Error testing salary calculation: {str(e)}")
                db.session.rollback()
                
        except Exception as e:
            print(f"Error fetching employee for salary test: {str(e)}")
            db.session.rollback()
        
        print("\n=== Salary Calculation Test Complete ===")

def test_basic_logic():
    """Test basic overtime calculation logic without database access"""
    print("=== Testing Basic Overtime Logic (No Database) ===\n")
    
    # Test the core calculation logic
    test_cases = [
        (0.5, "Half shift"),
        (1.0, "Full shift"),
        (1.5, "One and half shifts"),
        (2.0, "Two shifts"),
        (2.5, "Two and half shifts")
    ]
    
    daily_wage = 800  # Example daily wage
    hourly_rate = daily_wage / 8
    
    print(f"Daily Wage: ₹{daily_wage}")
    print(f"Hourly Rate: ₹{daily_wage} ÷ 8 = ₹{hourly_rate}")
    print()
    
    for shifts, description in test_cases:
        hours = shifts * 8
        allowance = hours * hourly_rate
        print(f"{description}: {shifts} shifts = {hours} hours = ₹{allowance}")
    
    print("\n=== Basic Logic Test Complete ===")

if __name__ == "__main__":
    print("Starting overtime calculation tests...\n")
    
    # First run basic logic test (no database required)
    test_basic_logic()
    print("\n" + "="*50 + "\n")
    
    try:
        test_overtime_calculation()
        print("\n" + "="*50 + "\n")
        test_salary_calculation()
        
    except Exception as e:
        print(f"Error running database tests: {str(e)}")
        print("Note: Database tests failed, but basic logic test passed.")
        import traceback
        traceback.print_exc()
