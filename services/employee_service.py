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
        last_name=payload.get("last_name", ""),
        father_name=payload.get("father_name"),
        address=payload.get("address"),
        adhar_number=payload.get("adhar_number") or payload.get("aadhaar_number"),
        place_of_birth=payload.get("place_of_birth"),
        marital_status=payload.get("marital_status"),
        date_of_birth=date_of_birth,
        email=payload.get("email"),
        phone_number=payload.get("phone_number") or payload.get("mobile_number"),
        hire_date=hire_date,
        job_title=payload.get("job_title") or payload.get("designation"),
        family_details=payload.get("family_details"),
        department_id=payload.get("department_id") or payload.get("department"),
        employment_status=payload.get("employment_status", "Active"),
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
        base_salary=payload.get("base_salary"),
        skill_category=payload.get("skill_category"),
        wage_rate=payload.get("wage_rate"),
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

    for sheet, df in sheet_frames.items():
        for idx, row in df.iterrows():
            try:
                # Split full name into first and last name
                full_name = str(row["Full Name"]).strip()
                name_parts = full_name.split(" ", 1)
                first_name = name_parts[0] if name_parts else ""
                last_name = name_parts[1] if len(name_parts) > 1 else ""

                payload = {
                    "first_name": first_name,
                    "last_name": last_name,
                    "date_of_birth": pd_to_date(row["Date of Birth"]),
                    "gender": str(row["Gender"]).strip() if not pd_isna(row["Gender"]) else None,
                    "site_name": str(row["Site Name"]).strip(),
                    "rank": str(row["Rank"]).strip(),
                    "state": str(row["State"]).strip(),
                    "base_salary": row["Base Salary"],
                    # add optional mappings as needed:
                    # "department": row.get("Department"),
                    # "employment_type": row.get("Employment Type"),
                }
                if not payload["first_name"]:
                    raise ValueError("First Name is required")

                # create
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
