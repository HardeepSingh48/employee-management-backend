import pandas as pd

# Basic required columns that should be present in any format
BASIC_REQUIRED_COLUMNS = [
    "Full Name", "Date of Birth", "Gender"
]

# Old format required columns (legacy support)
OLD_FORMAT_REQUIRED_COLUMNS = [
    "Full Name", "Date of Birth", "Gender",
    "Site Name", "Rank", "State", "Base Salary"
]

# New format required columns (comprehensive employee data)
NEW_FORMAT_REQUIRED_COLUMNS = [
    "Full Name", "Date of Birth", "Gender", "Marital Status",
    "Permanent Address", "Mobile Number", "Aadhaar Number",
    "PAN Card Number", "Date of Joining", "Employment Type",
    "Department", "Designation", "Work Location", "Salary Code"
]

def detect_excel_format(df):
    """Detect if this is the old format or new format"""
    columns = [col.strip() for col in df.columns.tolist()]

    # Check for old format indicators
    has_old_format = all(col in columns for col in ['Site Name', 'Rank', 'State', 'Base Salary'])

    # Check for new format indicators
    has_salary_code = any(col in columns for col in ['Salary Code', 'Salary_Code', 'SalaryCode'])
    has_comprehensive_fields = any(col in columns for col in ['Marital Status', 'Aadhaar Number', 'PAN Card Number'])

    if has_old_format and not has_salary_code:
        return 'old'
    elif has_salary_code or has_comprehensive_fields:
        return 'new'
    else:
        return 'basic'  # Has basic columns but not clearly old or new format

def load_excel_to_frames(file_storage):
    """
    Returns dict: {sheet_name: DataFrame}
    Validates columns based on detected format.
    """
    xls = pd.read_excel(file_storage, sheet_name=None)  # dict of dfs
    cleaned = {}

    for sheet, df in xls.items():
        if df.empty:
            continue

        # Strip headers
        df.columns = [str(c).strip() for c in df.columns]

        # Detect format
        format_type = detect_excel_format(df)

        # Validate based on format
        if format_type == 'old':
            # Validate old format
            missing = [c for c in OLD_FORMAT_REQUIRED_COLUMNS if c not in df.columns]
            if missing:
                raise ValueError(f"Sheet '{sheet}' (old format) missing columns: {missing}")
        elif format_type == 'new':
            # For new format, only check basic required columns since some fields might be optional
            missing = [c for c in BASIC_REQUIRED_COLUMNS if c not in df.columns]
            if missing:
                raise ValueError(f"Sheet '{sheet}' (new format) missing basic columns: {missing}")

            # Check for salary code specifically
            has_salary_code = any(col in df.columns for col in ['Salary Code', 'Salary_Code', 'SalaryCode'])
            if not has_salary_code:
                # If no salary code, warn but don't fail (might be optional in some cases)
                print(f"Warning: Sheet '{sheet}' doesn't have Salary Code column. Some employees might fail to import.")
        else:
            # Basic format - just check basic columns
            missing = [c for c in BASIC_REQUIRED_COLUMNS if c not in df.columns]
            if missing:
                raise ValueError(f"Sheet '{sheet}' missing basic columns: {missing}")

        cleaned[sheet] = df

    if not cleaned:
        raise ValueError("No non-empty sheets found.")
    return cleaned
