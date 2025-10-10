import os
import pandas as pd
from datetime import date
from utils.attendance_helpers import is_date, parse_date_from_column, normalize_attendance_value

def validate_excel_file(file, max_size_mb=10):
    """
    Validates Excel file before processing
    Returns: (is_valid: bool, errors: list[str])
    """
    errors = []

    # Check file extension
    allowed_extensions = {'.xlsx', '.xls'}
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        errors.append(f"Invalid file type '{file_ext}'. Only .xlsx and .xls files are allowed.")

    # Check file size
    file.seek(0, os.SEEK_END)
    file_size_mb = file.tell() / (1024 * 1024)
    file.seek(0)
    if file_size_mb > max_size_mb:
        errors.append(".2f")

    # Try reading file to check if it's corrupted
    try:
        file.seek(0)
        test_df = pd.read_excel(file, nrows=1)
        file.seek(0)
    except Exception as e:
        errors.append(f"File appears to be corrupted or unreadable: {str(e)}")

    return len(errors) == 0, errors

def validate_excel_structure(df):
    """
    Validates Excel structure and required columns
    Returns: (is_valid: bool, errors: list[str], warnings: list[str])
    """
    errors = []
    warnings = []

    # Check for empty dataframe
    if df.empty:
        errors.append("Excel file is empty. No data found.")
        return False, errors, warnings

    # Clean column names
    df.columns = df.columns.astype(str).str.strip()

    # Check for required columns
    required_columns = ['Employee ID', 'Employee Name']
    employee_id_col = None
    employee_name_col = None

    # Find Employee ID column (flexible matching)
    for col in df.columns:
        col_normalized = col.lower().replace(' ', '').replace('_', '')
        if col_normalized in ['employeeid', 'empid', 'id']:
            employee_id_col = col
        if col_normalized in ['employeename', 'name', 'empname']:
            employee_name_col = col

    if not employee_id_col:
        errors.append("Required column 'Employee ID' (or 'Emp ID'/'ID') not found in Excel file.")
    if not employee_name_col:
        errors.append("Required column 'Employee Name' (or 'Name'/'Emp Name') not found in Excel file.")

    # Check for date columns
    date_columns = []
    for col in df.columns:
        if col not in [employee_id_col, employee_name_col, 'Skill Level', 'Overtime'] and is_date(col):
            date_columns.append(col)

    if len(date_columns) == 0:
        errors.append("No valid date columns found. Expected format: DD/MM/YYYY, DD-MM-YYYY, or datetime objects.")

    # Check for duplicate column names
    if len(df.columns) != len(set(df.columns)):
        duplicate_cols = [col for col in df.columns if list(df.columns).count(col) > 1]
        errors.append(f"Duplicate column names found: {', '.join(set(duplicate_cols))}")

    # Check for completely empty rows
    empty_rows = df[df.isna().all(axis=1)]
    if len(empty_rows) > 0:
        warnings.append(f"{len(empty_rows)} completely empty row(s) found and will be skipped.")

    return len(errors) == 0, errors, warnings

def validate_employee_data(df, employee_id_col, employee_dict, user_role, site_id):
    """
    Validates employee data against database
    Returns: (validation_results: dict)
    """
    results = {
        'valid_employees': [],
        'invalid_employees': [],
        'missing_employees': [],
        'unauthorized_employees': [],
        'duplicate_employees': [],
        'empty_employee_ids': []
    }

    # Track seen employee IDs to detect duplicates
    seen_ids = set()
    duplicate_ids = set()

    # Validate each employee
    for idx, row in df.iterrows():
        emp_id_raw = row[employee_id_col]

        # Check for empty/null employee IDs
        if pd.isna(emp_id_raw) or str(emp_id_raw).strip() in ['', 'nan', 'NaN', 'None']:
            results['empty_employee_ids'].append({
                'row': idx + 2,  # +2 because Excel is 1-indexed and has header row
                'error': f"Empty employee ID in row {idx + 2}"
            })
            continue

        emp_id = str(emp_id_raw).strip()

        # Skip if still empty after stripping
        if not emp_id:
            results['empty_employee_ids'].append({
                'row': idx + 2,
                'error': f"Empty employee ID in row {idx + 2}"
            })
            continue

        # Check for duplicates
        if emp_id in seen_ids:
            duplicate_ids.add(emp_id)
        else:
            seen_ids.add(emp_id)

        # Check if employee exists in database
        if emp_id not in employee_dict:
            results['missing_employees'].append({
                'row': idx + 2,
                'employee_id': emp_id,
                'error': f"Employee ID '{emp_id}' not found in database"
            })
        else:
            # Check authorization (for supervisors)
            if user_role == 'supervisor':
                employee = employee_dict.get(emp_id)
                if not employee:
                    results['unauthorized_employees'].append({
                        'row': idx + 2,
                        'employee_id': emp_id,
                        'error': f"Employee ID '{emp_id}' not in your assigned site"
                    })
                else:
                    results['valid_employees'].append(emp_id)
            else:
                results['valid_employees'].append(emp_id)

    # Convert duplicate_ids set to list for results
    if duplicate_ids:
        results['duplicate_employees'] = list(duplicate_ids)

    return results

def validate_attendance_data(df, date_columns, month, year):
    """
    Validates attendance status values and dates
    Returns: (validation_results: dict)
    """
    results = {
        'valid_dates': [],
        'invalid_dates': [],
        'invalid_statuses': [],
        'out_of_range_dates': [],
        'month_mismatch': False
    }

    valid_statuses = ['P', 'A', 'O', 'Present', 'Absent', 'OFF', '']

    # Validate date columns
    for col in date_columns:
        year_from_col, month_from_col, day_from_col = parse_date_from_column(col)

        if not (year_from_col and month_from_col and day_from_col):
            results['invalid_dates'].append({
                'column': col,
                'error': f"Could not parse date from column '{col}'"
            })
            continue

        # Check if date is in expected month/year - this is now an error, not warning
        if month_from_col != month or year_from_col != year:
            results['out_of_range_dates'].append({
                'column': col,
                'date': f"{day_from_col}/{month_from_col}/{year_from_col}",
                'error': f"Date {day_from_col}/{month_from_col}/{year_from_col} is outside selected month {month}/{year}"
            })
            results['month_mismatch'] = True
            continue

        # Validate date exists
        try:
            date_obj = date(year_from_col, month_from_col, day_from_col)
            results['valid_dates'].append(col)
        except ValueError as e:
            results['invalid_dates'].append({
                'column': col,
                'error': f"Invalid date: {str(e)}"
            })

    # Validate attendance status values in cells
    for col in date_columns:
        if col in results['valid_dates']:
            for idx, value in df[col].items():
                if pd.notna(value):
                    status_str = str(value).strip().upper()
                    if status_str not in [s.upper() for s in valid_statuses]:
                        results['invalid_statuses'].append({
                            'row': idx + 2,
                            'column': col,
                            'value': value,
                            'error': f"Invalid attendance status '{value}'. Must be P, A, O, Present, Absent, or OFF"
                        })

    return results