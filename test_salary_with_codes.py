#!/usr/bin/env python3
"""
Test script to demonstrate salary calculation with salary codes
This shows how the system will work with actual employee salary codes
"""

import pandas as pd

def demonstrate_salary_calculation_logic():
    """Demonstrate the enhanced salary calculation logic"""
    
    print("🎯 Enhanced Salary Calculation Logic")
    print("=" * 60)
    print("Now using Employee Salary Codes for accurate wage rates!")
    print("=" * 60)
    
    # Sample employee data with salary codes
    print("📊 Sample Employee Data:")
    print("-" * 40)
    employees_data = [
        {
            'Employee ID': 'EMP001',
            'Name': 'John Doe',
            'Salary Code': 'SITE1-SUPERVISOR-MH',
            'Base Wage': 950.00,  # From WageMaster
            'Skill Level': 'Highly Skilled'
        },
        {
            'Employee ID': 'EMP002', 
            'Name': 'Jane Smith',
            'Salary Code': 'SITE2-OPERATOR-GJ',
            'Base Wage': 780.00,  # From WageMaster
            'Skill Level': 'Skilled'
        },
        {
            'Employee ID': 'EMP003',
            'Name': 'Bob Johnson', 
            'Salary Code': 'SITE1-HELPER-MH',
            'Base Wage': 650.00,  # From WageMaster
            'Skill Level': 'Semi-Skilled'
        }
    ]
    
    for emp in employees_data:
        print(f"  {emp['Employee ID']}: {emp['Name']}")
        print(f"    Salary Code: {emp['Salary Code']}")
        print(f"    Base Wage: ₹{emp['Base Wage']}/day (from WageMaster)")
        print(f"    Skill Level: {emp['Skill Level']}")
        print()
    
    # Sample attendance data
    print("📅 Sample Attendance Data (5-day work week):")
    print("-" * 40)
    attendance_data = {
        'Employee ID': ['EMP001', 'EMP002', 'EMP003'],
        'Employee Name': ['John Doe', 'Jane Smith', 'Bob Johnson'],
        'Monday': ['P', 'P', 'A'],
        'Tuesday': ['P', 'P', 'P'],
        'Wednesday': ['P', 'A', 'P'],
        'Thursday': ['P', 'P', 'P'],
        'Friday': ['P', 'P', 'P'],
        'Saturday': ['P', 'A', 'P'],  # Optional working day
        'Sunday': ['A', 'A', 'A']     # Holiday
    }
    
    df = pd.DataFrame(attendance_data)
    print(df.to_string(index=False))
    print()
    
    # Calculate salaries using the new logic
    print("💰 Salary Calculations (Using Salary Codes):")
    print("=" * 60)
    
    weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    attendance_cols = [col for col in df.columns if col in weekdays]
    
    results = []
    
    for _, row in df.iterrows():
        employee_id = row['Employee ID']
        employee_name = row['Employee Name']
        
        # Count present days
        days_present = sum(str(row[col]).strip().upper() == 'P' for col in attendance_cols)
        
        # Get wage from salary code (simulated)
        emp_data = next((emp for emp in employees_data if emp['Employee ID'] == employee_id), None)
        daily_wage = emp_data['Base Wage'] if emp_data else 526.0
        salary_code = emp_data['Salary Code'] if emp_data else 'N/A'
        
        # Calculate salary components
        basic = days_present * daily_wage
        pf = 0.12 * min(basic, 15000)
        esic = 0.0075 * min(basic, 21000)
        
        # Assume no additional earnings/deductions for this demo
        total_earnings = basic
        total_deductions = pf + esic
        net_salary = total_earnings - total_deductions
        
        result = {
            'Employee ID': employee_id,
            'Employee Name': employee_name,
            'Salary Code': salary_code,
            'Present Days': days_present,
            'Daily Wage': daily_wage,
            'Basic Salary': basic,
            'PF': pf,
            'ESIC': esic,
            'Total Earnings': total_earnings,
            'Total Deductions': total_deductions,
            'Net Salary': net_salary
        }
        
        results.append(result)
        
        # Display individual result
        print(f"👤 {employee_name} ({employee_id})")
        print(f"   Salary Code: {salary_code}")
        print(f"   Present Days: {days_present}")
        print(f"   Daily Wage: ₹{daily_wage:.2f} (from salary code)")
        print(f"   Basic Salary: ₹{basic:.2f}")
        print(f"   PF (12%): ₹{pf:.2f}")
        print(f"   ESIC (0.75%): ₹{esic:.2f}")
        print(f"   🎯 NET SALARY: ₹{net_salary:.2f}")
        print("-" * 40)
    
    # Summary
    total_basic = sum(r['Basic Salary'] for r in results)
    total_net = sum(r['Net Salary'] for r in results)
    
    print(f"📊 PAYROLL SUMMARY:")
    print(f"   Total Employees: {len(results)}")
    print(f"   Total Basic Salary: ₹{total_basic:.2f}")
    print(f"   🎯 TOTAL NET PAYROLL: ₹{total_net:.2f}")
    print()
    
    # Show the advantage
    print("✅ ADVANTAGES OF SALARY CODE SYSTEM:")
    print("-" * 40)
    print("1. ✅ Accurate wages based on employee's assigned salary code")
    print("2. ✅ Different wages for same skill level at different sites")
    print("3. ✅ Easy to update wages by modifying salary codes")
    print("4. ✅ Maintains audit trail of wage changes")
    print("5. ✅ Supports complex wage structures (site + rank + state)")
    print()
    
    # Show comparison with old system
    print("🔄 COMPARISON WITH FALLBACK SYSTEM:")
    print("-" * 40)
    fallback_wages = {
        'Highly Skilled': 868.00,
        'Skilled': 739.00,
        'Semi-Skilled': 614.00,
        'Un-Skilled': 526.00
    }
    
    for result in results:
        emp_data = next((emp for emp in employees_data if emp['Employee ID'] == result['Employee ID']), None)
        if emp_data:
            skill_level = emp_data['Skill Level']
            fallback_wage = fallback_wages.get(skill_level, 526.0)
            actual_wage = result['Daily Wage']
            difference = actual_wage - fallback_wage
            
            print(f"  {result['Employee ID']}: Salary Code ₹{actual_wage:.2f} vs Fallback ₹{fallback_wage:.2f} = {'+' if difference >= 0 else ''}₹{difference:.2f}")
    
    print()
    print("🎉 The salary calculation system now uses accurate wage rates!")
    print("   Each employee gets paid according to their specific salary code.")

if __name__ == "__main__":
    print("🚀 Salary Calculation with Salary Codes Demo")
    print("Demonstrating the enhanced salary calculation logic")
    print()
    
    demonstrate_salary_calculation_logic()
    
    print("\n" + "=" * 60)
    print("✅ Demo completed!")
    print("The system now correctly uses employee salary codes for wage rates! 🎉")
