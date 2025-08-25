#!/usr/bin/env python3
"""
Create a sample Excel file for bulk attendance upload testing
"""

import pandas as pd
from datetime import datetime, timedelta

def create_sample_attendance_excel():
    """Create a sample Excel file for bulk attendance upload"""
    
    print("Creating sample attendance Excel file...")
    
    # Sample employee data
    employees = [
        {'Employee ID': 'EMP001', 'Employee Name': 'John Doe', 'Skill Level': 'Senior'},
        {'Employee ID': 'EMP002', 'Employee Name': 'Jane Smith', 'Skill Level': 'Junior'},
        {'Employee ID': 'EMP003', 'Employee Name': 'Bob Johnson', 'Skill Level': 'Mid'},
        {'Employee ID': 'EMP004', 'Employee Name': 'Alice Brown', 'Skill Level': 'Senior'},
        {'Employee ID': 'EMP005', 'Employee Name': 'Charlie Wilson', 'Skill Level': 'Junior'}
    ]
    
    # Create date columns for August 2025 (example)
    start_date = datetime(2025, 8, 1)
    date_columns = []
    
    for i in range(31):  # August has 31 days
        current_date = start_date + timedelta(days=i)
        date_columns.append(current_date.strftime('%d/%m/%Y'))
    
    # Create the DataFrame
    data = []
    for emp in employees:
        row = {
            'Employee ID': emp['Employee ID'],
            'Employee Name': emp['Employee Name'],
            'Skill Level': emp['Skill Level']
        }
        
        # Add random attendance data for each date
        import random
        attendance_options = ['P', 'A', 'L', 'H']  # Present, Absent, Late, Half Day
        
        for date_col in date_columns:
            # Skip weekends (Saturday=5, Sunday=6)
            date_obj = datetime.strptime(date_col, '%d/%m/%Y')
            if date_obj.weekday() >= 5:  # Weekend
                row[date_col] = ''  # No attendance on weekends
            else:
                row[date_col] = random.choice(attendance_options)
        
        data.append(row)
    
    df = pd.DataFrame(data)
    
    # Save to Excel file
    filename = 'sample_attendance_upload.xlsx'
    df.to_excel(filename, index=False, engine='openpyxl')
    
    print(f"✅ Sample Excel file created: {filename}")
    print(f"✅ Contains {len(employees)} employees")
    print(f"✅ Contains {len(date_columns)} date columns")
    print(f"✅ File saved in: {filename}")
    
    print("\n📋 Instructions for supervisors:")
    print("1. Use this file as a template for bulk attendance upload")
    print("2. Modify the attendance values (P=Present, A=Absent, L=Late, H=Half Day)")
    print("3. Ensure Employee IDs match those in your system")
    print("4. Upload via the Bulk Attendance tab in the supervisor dashboard")
    
    return filename

if __name__ == "__main__":
    create_sample_attendance_excel()
