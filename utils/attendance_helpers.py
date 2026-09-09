
import pandas as pd
import re
import math
from datetime import datetime
import os


"""
Date utility functions for attendance processing
"""

def is_date(col):
    """Check if column name represents a date"""
    # Handle None or NaN values
    if col is None or (isinstance(col, float) and math.isnan(col)):
        return False

    # If it's already a datetime object or pandas Timestamp, accept it
    if isinstance(col, (datetime, pd.Timestamp)):
        return True

    # Convert to string and clean up
    try:
        col_str = str(col).strip()
    except:
        return False

    # Skip empty strings or common non-date columns
    if not col_str or col_str.lower() in ['employee id', 'employee name', 'skill level', 'emp id', 'name', 'nan', '']:
        return False

    # Check if it's a datetime string format (from pandas parsing)
    # Pattern for "YYYY-MM-DD HH:MM:SS" or "YYYY-MM-DD"
    datetime_patterns = [
        r'^\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}$',  # 2025-08-01 00:00:00
        r'^\d{4}-\d{2}-\d{2}$',                      # 2025-08-01
    ]
    
    for pattern in datetime_patterns:
        if re.match(pattern, col_str):
            try:
                # Try to parse as datetime
                if ' ' in col_str:
                    datetime.strptime(col_str, '%Y-%m-%d %H:%M:%S')
                else:
                    datetime.strptime(col_str, '%Y-%m-%d')
                return True
            except ValueError:
                continue

    # Pattern for dd/mm/yyyy, dd-mm-yyyy formats (original logic)
    date_patterns = [
        r'^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$',  # dd/mm/yyyy or dd-mm-yyyy
        r'^(\d{1,2})[/-](\d{1,2})[/-](\d{2})$',   # dd/mm/yy or dd-mm-yy
    ]
    
    for pattern in date_patterns:
        match = re.match(pattern, col_str)
        if match:
            try:
                day_str, month_str, year_str = match.groups()
                day = int(day_str)
                month = int(month_str)
                year = int(year_str)
                
                # Handle 2-digit years
                if year < 100:
                    year = 2000 + year if year < 30 else 1900 + year
                
                # Validate date ranges
                if not (1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= 2100):
                    continue
                
                # Try to create the date to validate it
                datetime(year, month, day)
                return True
            except (ValueError, TypeError, OverflowError):
                continue
    
    return False


def parse_date_from_column(col):
    """Parse date from column name"""
    # Handle None or NaN values
    if col is None or (isinstance(col, float) and math.isnan(col)):
        return None, None, None

    # If it's already a datetime object or pandas Timestamp, extract components
    if isinstance(col, (datetime, pd.Timestamp)):
        return col.year, col.month, col.day

    try:
        col_str = str(col).strip()
    except:
        return None, None, None
    
    # Check if it's a datetime string format (from pandas parsing)
    datetime_patterns = [
        r'^(\d{4})-(\d{2})-(\d{2})\s\d{2}:\d{2}:\d{2}$',  # 2025-08-01 00:00:00
        r'^(\d{4})-(\d{2})-(\d{2})$',                      # 2025-08-01
    ]
    
    for pattern in datetime_patterns:
        match = re.match(pattern, col_str)
        if match:
            try:
                year_str, month_str, day_str = match.groups()
                year = int(year_str)
                month = int(month_str)
                day = int(day_str)
                
                # Validate date ranges
                if not (1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= 2100):
                    continue
                
                # Try to create the date to validate it
                datetime(year, month, day)
                return year, month, day
            except (ValueError, TypeError, OverflowError):
                continue
    
    # Pattern for dd/mm/yyyy, dd-mm-yyyy formats (original logic)
    date_patterns = [
        r'^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$',  # dd/mm/yyyy or dd-mm-yyyy
        r'^(\d{1,2})[/-](\d{1,2})[/-](\d{2})$',   # dd/mm/yy or dd-mm-yy
    ]
    
    for pattern in date_patterns:
        match = re.match(pattern, col_str)
        if match:
            try:
                day_str, month_str, year_str = match.groups()
                day = int(day_str)
                month = int(month_str)
                year = int(year_str)
                
                # Handle 2-digit years
                if year < 100:
                    year = 2000 + year if year < 30 else 1900 + year
                
                # Validate date ranges
                if not (1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= 2100):
                    continue
                
                # Try to create the date to validate it
                datetime(year, month, day)
                return year, month, day
            except (ValueError, TypeError, OverflowError):
                continue
    
    return None, None, None


"""
Attendance utility functions for processing and validation
"""


STATUS_MAP = {
    'P': 'Present',
    'A': 'Absent',
    'O': 'OFF',
    'R': 'Reliever',
    'Present': 'Present',
    'Absent': 'Absent',
    'OFF': 'OFF',
    'Reliever': 'Reliever',
    'Reliever Duty': 'Reliever'
}

# Keep the canonical value as ``Reliever`` while accepting legacy values when
# reading historical records that may have been written before normalization.
RELIEVER_STATUSES = ('Reliever', 'R', 'Reliever Duty')

# The attendance rules use P for a regular working day and S/OFF for Sunday
# work.  Only S/OFF contributes to overtime; P contributes to basic wages.
OVERTIME_ELIGIBLE_STATUSES = ('OFF',)


def is_overtime_eligible(attendance_status):
    """Return True if overtime_shifts on this status should count toward payroll."""
    return attendance_status in OVERTIME_ELIGIBLE_STATUSES


def normalize_overtime_shifts_for_status(attendance_status, overtime_shifts):
    """Keep overtime only for statuses that are eligible for overtime pay."""
    if not is_overtime_eligible(attendance_status):
        return 0.0
    return float(overtime_shifts or 0.0)


def normalize_attendance_for_date(attendance_status, attendance_date, overtime_shifts=0.0):
    """Apply the P/R/S attendance rules before a record is persisted.

    Sunday work is represented by the existing ``OFF`` status (the system's
    stored equivalent of S) and receives at least one overtime shift.  R is
    kept as Reliever and never receives overtime.
    """
    status = normalize_attendance_value(attendance_status)
    if status is None:
        return None, 0.0

    shifts = float(overtime_shifts or 0.0)
    if attendance_date is not None and attendance_date.weekday() == 6 and status == 'Present':
        status = 'OFF'
        shifts = max(shifts, 1.0)

    return status, normalize_overtime_shifts_for_status(status, shifts)


def sum_eligible_overtime_shifts_sql():
    """SQLAlchemy expression: SUM(overtime_shifts) for Sunday/OFF rows only."""
    from sqlalchemy import case, func
    from models.attendance import Attendance

    return func.coalesce(
        func.sum(
            case(
                (Attendance.attendance_status.in_(OVERTIME_ELIGIBLE_STATUSES), Attendance.overtime_shifts),
                else_=0,
            )
        ),
        0,
    ).label('total_overtime_shifts')


def count_reliever_days_sql():
    """SQLAlchemy expression for the number of reliever-duty attendance days."""
    from sqlalchemy import case, func
    from models.attendance import Attendance

    return func.count(
        case((Attendance.attendance_status.in_(RELIEVER_STATUSES), 1))
    ).label('reliever_days')


def round_to_half(x):
    """Round to nearest 0.5 increment"""
    return round(x * 2) / 2.0


def normalize_attendance_value(value):
    """Normalize attendance value and return the mapped status"""
    if not value or pd.isna(value):
        return None

    # Convert to string and clean up
    v = str(value).strip().upper()

    # Handle common variations
    if v in ['P', 'PRESENT']:
        return 'Present'
    elif v in ['A', 'ABSENT']:
        return 'Absent'
    elif v in ['O', 'OFF']:
        return 'OFF'
    elif v in ['R', 'RELIEVER', 'RELIEVER DUTY']:
        return 'Reliever'
    else:
        # Try original mapping as fallback
        return STATUS_MAP.get(v.title())

"""
Validation utilities for attendance data
"""

def validate_file_upload(request):
    """Validate file upload requirements"""
    if 'file' not in request.files:
        return False, "No file uploaded"
    
    file = request.files['file']
    if not file or file.filename == '':
        return False, "No file selected"
    
    return True, file


def validate_file_type(filename):
    """Validate that file is an Excel file"""
    allowed_extensions = {'.xlsx', '.xls'}
    file_ext = os.path.splitext(filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        return False, "Invalid file type. Please upload an Excel file (.xlsx or .xls)"
    
    return True, None


def validate_required_columns(df, required_columns):
    """Validate that required columns are present in DataFrame"""
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        return False, f"Missing required columns: {', '.join(missing_columns)}"
    
    return True, None


def validate_employee_access(current_user, employee_id):
    """Validate that current user has access to employee data"""
    from models.employee import Employee

    employee = Employee.query.filter_by(employee_id=employee_id).first()
    
    if not employee:
        return False, f"Employee {employee_id} not found"
    
    # For supervisors, check if employee belongs to their site
    if current_user.role == 'supervisor' and employee.site_id != current_user.site_id:
        return False, f"Employee {employee_id} not in your site"
    
    return True, employee


def validate_overtime_shifts(overtime_shifts):
    """Validate overtime shifts value"""
    if overtime_shifts < 0:
        return False, "Overtime shifts cannot be negative"
    
    return True, None


def validate_date_params(year, month):
    """Validate year and month parameters"""
    try:
        year = int(year)
        month = int(month)
    except ValueError:
        return False, "Invalid month or year format", None, None
    
    if month < 1 or month > 12:
        return False, "Month must be between 1 and 12", None, None
    
    return True, None, year, month
