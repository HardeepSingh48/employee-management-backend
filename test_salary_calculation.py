#!/usr/bin/env python3
"""
Test script to verify salary calculation logic
This script tests your exact salary calculation logic without requiring the full Flask app
"""

import pandas as pd
import sys
import os

# Add the current directory to Python path to import services
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.salary_service import SalaryService

def test_salary_calculation():
    """Test the salary calculation with sample data"""

    print("🧪 Testing Salary Calculation Logic")
    print("=" * 50)
    print("⚠️  Note: This test uses fallback skill level mapping since no database connection.")
    print("   In production, wages will be fetched from employee salary codes.")
    print("=" * 50)

    # Create sample attendance data (matching your expected format)
    sample_data = {
        'Employee ID': ['EMP001', 'EMP002', 'EMP003'],
        'Employee Name': ['John Doe', 'Jane Smith', 'Bob Johnson'],
        'Skill Level': ['Highly Skilled', 'Skilled', 'Semi-Skilled'],
        'Monday': ['P', 'P', 'A'],
        'Tuesday': ['P', 'P', 'P'],
        'Wednesday': ['P', 'A', 'P'],
        'Thursday': ['P', 'P', 'P'],
        'Friday': ['P', 'P', 'P'],
        'Saturday': ['P', 'A', 'P'],
        'Sunday': ['A', 'A', 'A']
    }
    
    # Create sample adjustments data
    adjustments_data = {
        'Employee ID': ['EMP001', 'EMP002'],
        'Special Basic': [1000, 1500],
        'DA': [500, 600],
        'HRA': [2000, 2500],
        'Overtime': [1200, 800],
        'Others': [300, 200],
        'Society': [100, 150],
        'Income Tax': [2000, 2500],
        'Insurance': [500, 600],
        'Others Recoveries': [200, 100]
    }
    
    # Convert to DataFrames
    df = pd.DataFrame(sample_data)
    adj_df = pd.DataFrame(adjustments_data)
    
    print("📊 Sample Attendance Data:")
    print(df.to_string(index=False))
    print("\n📊 Sample Adjustments Data:")
    print(adj_df.to_string(index=False))
    print("\n" + "=" * 50)
    
    # Test the salary calculation
    try:
        result = SalaryService.calculate_salary_from_attendance_data(df, adj_df)
        
        if result['success']:
            print("✅ Salary Calculation Successful!")
            print(f"📈 Processed {len(result['data'])} employees")
            print("\n💰 Salary Calculation Results:")
            print("-" * 80)
            
            # Display results in a formatted way
            for emp in result['data']:
                print(f"Employee: {emp['Employee Name']} ({emp['Employee ID']})")
                print(f"  Skill Level: {emp['Skill Level']}")
                print(f"  Present Days: {emp['Present Days']}")
                print(f"  Daily Wage: ₹{emp['Daily Wage']:.2f}")
                print(f"  Basic Salary: ₹{emp['Basic']:.2f}")
                print(f"  Total Earnings: ₹{emp['Total Earnings']:.2f}")
                print(f"  PF: ₹{emp['PF']:.2f}")
                print(f"  ESIC: ₹{emp['ESIC']:.2f}")
                print(f"  Total Deductions: ₹{emp['Total Deductions']:.2f}")
                print(f"  🎯 NET SALARY: ₹{emp['Net Salary']:.2f}")
                print("-" * 40)
            
            # Calculate totals
            total_basic = sum(emp['Basic'] for emp in result['data'])
            total_earnings = sum(emp['Total Earnings'] for emp in result['data'])
            total_deductions = sum(emp['Total Deductions'] for emp in result['data'])
            total_net = sum(emp['Net Salary'] for emp in result['data'])
            
            print(f"\n📊 SUMMARY:")
            print(f"  Total Basic Salary: ₹{total_basic:.2f}")
            print(f"  Total Earnings: ₹{total_earnings:.2f}")
            print(f"  Total Deductions: ₹{total_deductions:.2f}")
            print(f"  🎯 TOTAL NET PAYROLL: ₹{total_net:.2f}")
            
        else:
            print("❌ Salary Calculation Failed!")
            print(f"Error: {result['message']}")
            if 'error' in result:
                print(f"Details: {result['error']}")
                
    except Exception as e:
        print(f"❌ Test Failed with Exception: {str(e)}")
        import traceback
        traceback.print_exc()

def test_wage_rates():
    """Test the wage rate mapping"""
    print("\n🏷️  Testing Wage Rate Mapping")
    print("=" * 30)
    
    for skill_level, wage in SalaryService.wage_map.items():
        print(f"{skill_level}: ₹{wage:.2f}/day")

if __name__ == "__main__":
    print("🚀 Starting Salary Calculation Tests")
    print("Using your exact salary calculation logic")
    print("=" * 60)
    
    test_wage_rates()
    test_salary_calculation()
    
    print("\n✅ Test completed!")
    print("If you see salary results above, your logic is working correctly! 🎉")
