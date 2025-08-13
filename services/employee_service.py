from sqlalchemy import and_
from models import db
from models.employee import Employee
from models.wage_master import WageMaster
from models.account_details import AccountDetails
from datetime import datetime

def _next_employee_id() -> str:
    """
    EMP001-style generator based on highest existing employee_id numeric suffix.
    """
    last = db.session.query(Employee).order_by(Employee.employee_id.desc()).first()
    if not last or not last.employee_id:
        return "EMP001"
    try:
        n = int(last.employee_id.replace("EMP", "")) + 1
    except ValueError:
        n = 1
    return f"EMP{n:03d}"

def _get_or_create_wage_master(site_name: str, rank: str, state: str, base_salary, skill_level="Skilled"):
    # Exact match
    wm = WageMaster.query.filter_by(site_name=site_name, rank=rank, state=state, is_active=True).first()
    if wm:
        return wm.salary_code

    # Fallback: first 3 characters match for site_name
    prefix = (site_name or "")[:3]
    wm = WageMaster.query.filter(
        WageMaster.rank == rank,
        WageMaster.state == state,
        WageMaster.site_name.ilike(f"{prefix}%"),
        WageMaster.is_active == True
    ).first()
    if wm:
        return wm.salary_code

    # Generate salary code
    salary_code = _generate_salary_code(site_name, rank, state)

    # Create new
    wm = WageMaster(
        salary_code=salary_code,
        site_name=site_name,
        rank=rank,
        state=state,
        base_wage=base_salary or 0,
        skill_level=skill_level
    )
    db.session.add(wm)
    db.session.flush()  # get wm.id
    return wm.salary_code

def _generate_salary_code(site_name: str, rank: str, state: str) -> str:
    """Generate salary code from site name, rank, and state"""
    import re

    # Clean and format inputs
    site_clean = re.sub(r'[^a-zA-Z]', '', site_name.upper())
    rank_clean = re.sub(r'[^a-zA-Z]', '', rank.upper())
    state_clean = re.sub(r'[^a-zA-Z]', '', state.upper())

    # Extract site prefix (first 3 characters)
    site_prefix = site_clean[:3] if len(site_clean) >= 3 else site_clean

    # Basic code format
    base_code = f"{site_prefix}{rank_clean}{state_clean}"

    # Check if code already exists
    existing_code = WageMaster.query.filter(WageMaster.salary_code == base_code).first()

    if not existing_code:
        return base_code

    # If exists, add a numeric suffix
    counter = 1
    while True:
        new_code = f"{base_code}{counter:02d}"
        existing = WageMaster.query.filter(WageMaster.salary_code == new_code).first()
        if not existing:
            return new_code
        counter += 1

def create_employee(payload: dict) -> Employee:
    # Get salary code from payload (admin must provide existing salary code)
    salary_code = payload.get("salary_code")

    # If salary code is provided, validate it exists and update skill level
    if salary_code:
        wage_master = WageMaster.query.filter_by(salary_code=salary_code, is_active=True).first()
        if not wage_master:
            raise ValueError(f"Invalid salary code: {salary_code}. Please use an existing salary code.")

        # Update skill level in wage master if provided during employee registration
        employee_skill_level = payload.get("skill_level")
        if employee_skill_level and wage_master.skill_level == "Not Specified":
            wage_master.skill_level = employee_skill_level
            db.session.add(wage_master)
    else:
        # Legacy support: create salary code if site_name, rank, state provided
        if all(k in payload for k in ("site_name", "rank", "state", "base_salary")):
            salary_code = _get_or_create_wage_master(
                payload.get("site_name"),
                payload.get("rank"),
                payload.get("state"),
                payload.get("base_salary"),
                payload.get("skill_level", "Skilled")
            )

    # Parse date fields
    date_of_birth = _parse_date(payload.get("date_of_birth"))
    hire_date = _parse_date(payload.get("hire_date") or payload.get("date_of_joining"))

    emp = Employee(
        employee_id=_next_employee_id(),
        first_name=payload.get("first_name", ""),
        last_name=payload.get("last_name", "") or "",  # Handle None values
        #father_name=payload.get("father_name"),
        address=payload.get("address"),
        adhar_number=payload.get("adhar_number") or payload.get("aadhaar_number"),
        #place_of_birth=payload.get("place_of_birth"),
        marital_status=payload.get("marital_status"),
        date_of_birth=date_of_birth,
        email=payload.get("email"),
        phone_number=payload.get("phone_number") or payload.get("mobile_number"),
        hire_date=hire_date,
        #job_title=payload.get("job_title") or payload.get("designation"),
        #family_details=payload.get("family_details"),
        department_id=payload.get("department_id") or payload.get("department"),
        #employment_status=payload.get("employment_status", "Active"),
        gender=payload.get("gender"),
        nationality=payload.get("nationality", "Indian"),
        blood_group=payload.get("blood_group"),
        alternate_contact_number=payload.get("alternate_contact_number"),
        pan_card_number=payload.get("pan_card_number"),
        voter_id_driving_license=payload.get("voter_id_driving_license"),
        uan=payload.get("uan"),
        esic_number=payload.get("esic_number"),
        employment_type=payload.get("employment_type"),
        designation=payload.get("designation"),
        work_location=payload.get("work_location"),
        reporting_manager=payload.get("reporting_manager"),
        skill_category=payload.get("skill_category"),
        pf_applicability=bool(payload.get("pf_applicability", False)),
        esic_applicability=bool(payload.get("esic_applicability", False)),
        professional_tax_applicability=bool(payload.get("professional_tax_applicability", False)),
        salary_advance_loan=payload.get("salary_advance_loan"),
        highest_qualification=payload.get("highest_qualification"),
        year_of_passing=payload.get("year_of_passing"),
        additional_certifications=payload.get("additional_certifications"),
        experience_duration=payload.get("experience_duration"),
        emergency_contact_name=payload.get("emergency_contact_name"),
        emergency_contact_relationship=payload.get("emergency_contact_relationship"),
        emergency_contact_phone=payload.get("emergency_contact_phone"),
        salary_code=salary_code,
        created_by=payload.get("created_by", "system")
    )

    db.session.add(emp)
    db.session.flush()  # Get the employee ID

    # Create account details if bank information is provided
    if payload.get("bank_account_number") and payload.get("ifsc_code"):
        account_details = AccountDetails(
            emp_id=emp.employee_id,
            account_number=payload.get("bank_account_number"),
            ifsc_code=payload.get("ifsc_code"),
            bank_name=payload.get("bank_name"),
            branch_name=payload.get("branch_name"),
            created_by=payload.get("created_by", "system")
        )
        db.session.add(account_details)

    db.session.commit()
    return emp

def _parse_date(date_str):
    """Parse date string to date object"""
    if not date_str:
        return None

    if isinstance(date_str, datetime):
        return date_str.date()

    # Try different date formats
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(str(date_str), fmt).date()
        except ValueError:
            continue

    return None

def bulk_import_from_frames(sheet_frames: dict) -> dict:
    """
    sheet_frames: dict {sheet_name: DataFrame}
    Returns a summary: {"inserted": n, "errors": [row_error, ...]}
    """
    summary = {"inserted": 0, "errors": []}

    # Department mapping (Excel name -> DB ID)
    department_mapping = {
        'HR': 'HR',
        'IT': 'IT',
        'Finance': 'FIN',
        'Marketing': 'MKT',
        'Operations': 'OPS',
        'Sales': 'SAL',
        'Engineering': 'ENG',
        'Customer Support': 'CS',
        'Legal': 'LEG',
        'Administration': 'ADM'
    }

    def detect_format(df):
        """Detect if this is the old format (Site Name, Rank, State) or new format (Salary Code)"""
        columns = [col.strip() for col in df.columns.tolist()]
        has_old_format = all(col in columns for col in ['Site Name', 'Rank', 'State'])
        has_new_format = any(col in columns for col in ['Salary Code', 'Salary_Code', 'SalaryCode'])
        return 'old' if has_old_format else 'new' if has_new_format else 'unknown'

    for sheet, df in sheet_frames.items():
        # Detect the format of this sheet
        format_type = detect_format(df)

        if format_type == 'unknown':
            summary["errors"].append({
                "sheet": sheet,
                "row_index": 0,
                "error": "Unknown format. Sheet must contain either 'Salary Code' column or 'Site Name', 'Rank', 'State' columns"
            })
            continue

        for idx, row in df.iterrows():
            try:
                # Split full name into first and last name
                full_name = str(row["Full Name"]).strip()
                name_parts = full_name.split(" ", 1)
                first_name = name_parts[0] if name_parts else ""
                last_name = name_parts[1] if len(name_parts) > 1 else ""

                if not first_name:
                    raise ValueError("Full Name is required")

                # Helper function to get value or None with flexible column name matching
                def get_value(column_name, default=None, alternatives=None):
                    """Get value from row with flexible column name matching"""
                    if alternatives is None:
                        alternatives = []

                    # Try exact match first
                    for col_name in [column_name] + alternatives:
                        if col_name in row:
                            try:
                                val = row.get(col_name)
                                if pd_isna(val) or str(val).strip() == '':
                                    return default
                                return str(val).strip()
                            except:
                                continue
                    return default

                def get_bool_value(column_name, default=False, alternatives=None):
                    """Get boolean value with flexible column name matching"""
                    if alternatives is None:
                        alternatives = []

                    for col_name in [column_name] + alternatives:
                        if col_name in row:
                            try:
                                val = row.get(col_name)
                                if pd_isna(val):
                                    return default
                                val_str = str(val).strip().upper()
                                # Handle various boolean representations
                                return val_str in ['TRUE', '1', 'YES', 'Y', 'T']
                            except:
                                continue
                    return default

                def get_number_value(column_name, default=0, alternatives=None):
                    # Try the main column name first
                    try:
                        val = row.get(column_name)
                        if not pd_isna(val) and str(val).strip() != '':
                            return float(val)
                    except:
                        pass

                    # Try alternative column names if provided
                    if alternatives:
                        for alt_name in alternatives:
                            try:
                                val = row.get(alt_name)
                                if not pd_isna(val) and str(val).strip() != '':
                                    return float(val)
                            except:
                                continue

                    return default

                # Map department name to department ID
                department_name = get_value("Department")
                department_id = department_mapping.get(department_name, department_name)

                # Create base payload with flexible column name matching
                payload = {
                    "first_name": first_name,
                    "last_name": last_name,
                    "date_of_birth": pd_to_date(get_value("Date of Birth")),
                    "gender": get_value("Gender"),
                    "marital_status": get_value("Marital Status"),
                    "nationality": get_value("Nationality", "Indian"),
                    "blood_group": get_value("Blood Group"),
                    "address": get_value("Permanent Address", alternatives=["Address"]),
                    "phone_number": get_value("Mobile Number", alternatives=["Phone Number", "Mobile"]),
                    "alternate_contact_number": get_value("Alternate Contact Number", alternatives=["Alt Contact", "Alternate Phone"]),
                    "adhar_number": get_value("Aadhaar Number", alternatives=["Aadhar Number", "Aadhaar"]),
                    "pan_card_number": get_value("PAN Card Number", alternatives=["PAN Number", "PAN"]),
                    "voter_id_driving_license": get_value("Voter ID / Driving License", alternatives=["Voter ID", "DL Number"]),
                    "uan": get_value("UAN"),
                    "esic_number": get_value("ESIC Number", alternatives=["ESIC"]),
                    "hire_date": pd_to_date(get_value("Date of Joining", alternatives=["Joining Date", "DOJ"])),
                    "employment_type": get_value("Employment Type", alternatives=["Emp Type"]),
                    "department_id": department_id,
                    "designation": get_value("Designation", alternatives=["Position", "Role"]),
                    "work_location": get_value("Work Location", alternatives=["Location", "Office"]),
                    "reporting_manager": get_value("Reporting Manager", alternatives=["Manager", "Supervisor"]),
                    "skill_category": get_value("Skill Category", alternatives=["Skills", "Category"]),
                    "pf_applicability": get_bool_value("PF Applicability", alternatives=["PF"]),
                    "esic_applicability": get_bool_value("ESIC Applicability", alternatives=["ESIC"]),
                    "professional_tax_applicability": get_bool_value("Professional Tax Applicability", alternatives=["Prof Tax", "PT"]),
                    "salary_advance_loan": get_number_value("Salary Advance/Loan", alternatives=["Advance", "Loan"]),
                    "bank_account_number": get_value("Bank Account Number", alternatives=["Account Number", "Bank Account"]),
                    "bank_name": get_value("Bank Name", alternatives=["Bank"]),
                    "ifsc_code": get_value("IFSC Code", alternatives=["IFSC"]),
                    "highest_qualification": get_value("Highest Qualification", alternatives=["Qualification", "Education"]),
                    "year_of_passing": get_value("Year of Passing", alternatives=["Passing Year", "Year"]),
                    "additional_certifications": get_value("Additional Certifications", alternatives=["Certifications", "Certs"]),
                    "experience_duration": get_number_value("Experience Duration", alternatives=["Experience", "Exp"]),
                    "emergency_contact_name": get_value("Emergency Contact Name", alternatives=["Emergency Contact", "EC Name"]),
                    "emergency_contact_relationship": get_value("Emergency Relationship", alternatives=["EC Relationship", "Relationship"]),
                    "emergency_contact_phone": get_value("Emergency Phone Number", alternatives=["Emergency Phone", "EC Phone"]),
                }

                # Handle different formats
                if format_type == 'new':
                    # New format with Salary Code
                    salary_code = get_value("Salary Code", alternatives=["Salary_Code", "SalaryCode"])
                    if not salary_code:
                        raise ValueError("Salary Code is required for new format. Please ensure the Salary Code column has valid values.")
                    payload["salary_code"] = salary_code
                elif format_type == 'old':
                    # Old format with Site Name, Rank, State, Base Salary
                    payload["site_name"] = get_value("Site Name")
                    payload["rank"] = get_value("Rank")
                    payload["state"] = get_value("State")
                    payload["base_salary"] = get_number_value("Base Salary")

                # Remove None values to avoid issues (but keep empty strings for optional fields)
                payload = {k: v for k, v in payload.items() if v is not None}

                # create employee
                _ = create_employee(payload)
                summary["inserted"] += 1
            except Exception as e:
                summary["errors"].append(
                    {"sheet": sheet, "row_index": int(idx), "error": str(e)}
                )

    return summary

# Helpers for date coercion without importing pandas here
from datetime import datetime
def pd_isna(v):
    try:
        import pandas as pd
        return pd.isna(v)
    except Exception:
        return v is None

def pd_to_date(v):
    if v is None or pd_isna(v) or str(v).strip() == "":
        return None
    if isinstance(v, datetime):
        return v.date()
    # try to parse common formats
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(str(v), fmt).date()
        except ValueError:
            continue
    # excel serial number?
    try:
        import pandas as pd
        if isinstance(v, (int, float)):
            return pd.to_datetime(v, unit="D", origin="1899-12-30").date()
    except Exception:
        pass
    # last resort
    try:
        return datetime.fromisoformat(str(v)).date()
    except Exception:
        return None


def get_employee_by_id(employee_id: str) -> Employee:
    """Get employee by employee ID"""
    return Employee.query.filter_by(employee_id=employee_id).first()


def get_all_employees(page: int = 1, per_page: int = 10):
    """Get all employees with pagination"""
    return Employee.query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )


def search_employees(search_term: str = "", department: str = None, employment_status: str = None):
    """Search employees by various criteria"""
    query = Employee.query

    if search_term:
        search_filter = f"%{search_term}%"
        query = query.filter(
            db.or_(
                Employee.first_name.ilike(search_filter),
                Employee.last_name.ilike(search_filter),
                Employee.employee_id.ilike(search_filter),
                Employee.email.ilike(search_filter)
            )
        )

    if department:
        query = query.filter(Employee.department_id == department)

    if employment_status:
        query = query.filter(Employee.employment_status == employment_status)

    return query.all()
