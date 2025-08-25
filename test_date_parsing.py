#!/usr/bin/env python3
"""
Test script to verify date parsing functions
"""

import re
from datetime import datetime

def is_date(col):
    """
    Check if a column name represents a valid date in dd/mm/yyyy format
    """
    # Pattern for dd/mm/yyyy or dd-mm-yyyy format
    date_pattern = r'^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$'
    
    match = re.match(date_pattern, str(col).strip())
    if not match:
        return False
    
    try:
        day, month, year = match.groups()
        # Validate the date
        datetime(int(year), int(month), int(day))
        return True
    except ValueError:
        return False

def parse_date_from_column(col):
    """
    Parse date from column name in dd/mm/yyyy format
    Returns (year, month, day) tuple
    """
    date_pattern = r'^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$'
    match = re.match(date_pattern, str(col).strip())
    
    if match:
        day, month, year = match.groups()
        return int(year), int(month), int(day)
    
    return None, None, None

def test_date_functions():
    """Test the date parsing functions"""
    
    print("Testing Date Parsing Functions")
    print("=" * 50)
    
    # Test cases
    test_columns = [
        "01/08/2025",
        "15/12/2024", 
        "31-01-2025",
        "05-06-2024",
        "Employee ID",
        "Full Name",
        "Skill Level",
        "01/13/2025",  # Invalid month
        "32/01/2025",  # Invalid day
        "01/08/25",    # Wrong year format
        "2025-08-01",  # Wrong format
        "01.08.2025",  # Wrong separator
        "",
        None
    ]
    
    for col in test_columns:
        is_valid = is_date(col)
        year, month, day = parse_date_from_column(col)
        
        print(f"Column: '{col}'")
        print(f"  Is Date: {is_valid}")
        print(f"  Parsed: Year={year}, Month={month}, Day={day}")
        print()
    
    print("=" * 50)
    print("Test completed!")

if __name__ == "__main__":
    test_date_functions()
