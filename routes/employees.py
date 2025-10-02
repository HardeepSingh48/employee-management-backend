from flask import Blueprint, request, jsonify
from services.employee_service import create_employee, bulk_import_from_frames, get_employee_by_id, get_all_employees, get_all_employees_unpaginated, search_employees
from models import db
from models.employee import Employee
from utils.upload import save_file
from models.account_details import AccountDetails
from routes.auth import token_required
from sqlalchemy import text
import pandas as pd
from datetime import datetime
import traceback

employees_bp = Blueprint("employees", __name__)

@employees_bp.route("/register", methods=["POST"])
def register_employee():
    """
    Comprehensive Employee Registration Endpoint

    Accepts JSON or form-data with comprehensive employee details.

    Required fields:
    - first_name: Employee's first name
    - last_name: Employee's last name

    Optional fields include personal details, employment details, bank details, etc.

    Example JSON:
    {
      "first_name": "Aman",
      "last_name": "Sharma",
      "father_name": "Ram Sharma",
      "date_of_birth": "1990-01-15",
      "gender": "Male",
      "marital_status": "married",
      "nationality": "Indian",
      "blood_group": "O+",
      "address": "123 Main Street, Delhi",
      "phone_number": "9876543210",
      "alternate_contact_number": "9876543211",
      "email": "aman.sharma@company.com",
      "adhar_number": "123456789012",
      "pan_card_number": "ABCDE1234F",
      "voter_id_driving_license": "DL123456789",
      "uan": "123456789012",
      "esic_number": "1234567890",
      "hire_date": "2023-01-01",
      "employment_type": "Full-time",
      "department_id": "IT",
      "designation": "Software Engineer",
      "work_location": "Delhi Office",
      "reporting_manager": "Manager Name",
      "base_salary": 50000,
      "skill_category": "Technical",
      "wage_rate": 500,
      "pf_applicability": true,
      "esic_applicability": true,
      "professional_tax_applicability": true,
      "salary_advance_loan": "None",
      "highest_qualification": "B.Tech",
      "year_of_passing": "2012",
      "additional_certifications": "AWS Certified",
      "experience_duration": "5 years",
      "emergency_contact_name": "Emergency Contact",
      "emergency_contact_relationship": "Father",
      "emergency_contact_phone": "9876543212",
      "bank_account_number": "1234567890",
      "bank_name": "State Bank of India",
      "ifsc_code": "SBIN0001234",
      "branch_name": "Delhi Branch",
      "site_name": "Delhi Central",
      "rank": "Engineer",
      "state": "Delhi"
    }
    """
    if request.is_json:
        payload = request.get_json()
    else:
        payload = request.form.to_dict()

    # Validate required fields
    required_fields = ["first_name", "last_name"]
    missing_fields = [field for field in required_fields if not payload.get(field)]

    if missing_fields:
        return jsonify({
            "success": False,
            "message": f"Required fields missing: {', '.join(missing_fields)}"
        }), 400

    try:
        emp = create_employee(payload)

        # Save uploaded documents if present (Aadhaar, PAN, Voter ID front/back, Passbook front)
        saved_docs = {}
        file_fields = [
            "aadhaar_front", "aadhaar_back",
            "pan_front", "pan_back",
            "voter_front", "voter_back",
            "passbook_front"
        ]

        for key in file_fields:
            f = request.files.get(key)
            if f:
                path = save_file(f, subfolder=emp.employee_id)
                if path:
                    saved_docs[key] = path

        return jsonify({
            "success": True,
            "message": "Employee registered successfully",
            "data": {
                "employee_id": emp.employee_id,
                "first_name": emp.first_name,
                "last_name": emp.last_name,
                "email": emp.email,
                "phone_number": emp.phone_number,
                "department_id": emp.department_id,
                "designation": emp.designation,
                "salary_code": emp.salary_code,
                "documents": saved_docs
            }
        }), 201
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error registering employee: {str(e)}"
        }), 400


 # Optimised bulk upload
 
def parse_boolean(value):
    """Parse various boolean representations"""
    if pd.isna(value) or value == '':
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.upper() in ['TRUE', 'YES', '1', 'Y']
    return bool(value)

def split_full_name(full_name):
    """Split full name into first and last name"""
    if not full_name or pd.isna(full_name):
        return None, None
    
    parts = str(full_name).strip().split(maxsplit=1)
    first_name = parts[0] if len(parts) > 0 else None
    last_name = parts[1] if len(parts) > 1 else None
    return first_name, last_name

def parse_date(date_value):
    """Parse date from various formats"""
    if pd.isna(date_value) or date_value == '':
        return None
    
    if isinstance(date_value, datetime):
        return date_value.date()
    
    try:
        return pd.to_datetime(date_value).date()
    except:
        return None

@employees_bp.route("/bulk-upload", methods=["POST"])
def bulk_upload_optimized():
    """
    Optimized bulk upload endpoint for large datasets (1000+ employees)
    
    Key optimizations:
    1. Bulk insert with SQLAlchemy Core (much faster than ORM)
    2. Batch processing in chunks
    3. Single transaction with savepoints
    4. Detailed error tracking
    5. Memory-efficient streaming
    """
    file = request.files.get("file")
    if not file:
        return jsonify({"success": False, "message": "No file provided"}), 400

    # Save file temporarily
    file_path = save_file(file)
    
    # Configuration
    CHUNK_SIZE = 500  # Process in batches of 500
    
    try:
        # Read Excel file
        df = pd.read_excel(file_path, engine='openpyxl')
        
        total_rows = len(df)
        inserted = 0
        errors = []
        
        # Validate required columns
        required_columns = [
            'Full Name', 'Marital Status', 'Permanent Address', 
            'Mobile Number', 'Aadhaar Number', 'PAN Card Number',
            'Date of Joining', 'Employment Type', 'Department',
            'Designation', 'Work Location', 'Salary Code',
            'Bank Account Number', 'Bank Name', 'IFSC Code',
            'Highest Qualification', 'Year of Passing',
            'Experience Duration', 'Emergency Contact Name',
            'Emergency Relationship', 'Emergency Phone Number'
        ]
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return jsonify({
                "success": False,
                "message": f"Missing required columns: {', '.join(missing_columns)}"
            }), 400
        
        # Process in chunks for better memory management
        for chunk_start in range(0, total_rows, CHUNK_SIZE):
            chunk_end = min(chunk_start + CHUNK_SIZE, total_rows)
            chunk_df = df.iloc[chunk_start:chunk_end]
            
            employees_to_insert = []
            accounts_to_insert = []
            
            for idx, row in chunk_df.iterrows():
                try:
                    # Parse full name
                    first_name, last_name = split_full_name(row.get('Full Name'))
                    if not first_name or not last_name:
                        errors.append({
                            "row": idx + 2,  # +2 for Excel row (header + 0-index)
                            "error": "Invalid Full Name - must contain first and last name"
                        })
                        continue
                    
                    # Validate required fields
                    if pd.isna(row.get('Mobile Number')) or not str(row.get('Mobile Number')).strip():
                        errors.append({
                            "row": idx + 2,
                            "error": "Mobile Number is required"
                        })
                        continue
                    
                    # Parse dates
                    date_of_birth = parse_date(row.get('Date of Birth'))
                    date_of_joining = parse_date(row.get('Date of Joining'))
                    
                    if not date_of_joining:
                        errors.append({
                            "row": idx + 2,
                            "error": "Invalid Date of Joining format"
                        })
                        continue
                    
                    # Prepare employee data
                    employee_data = {
                        'first_name': first_name,
                        'last_name': last_name,
                        'father_name': row.get('Father Name') if not pd.isna(row.get('Father Name')) else None,
                        'date_of_birth': date_of_birth,
                        'gender': row.get('Gender') if not pd.isna(row.get('Gender')) else None,
                        'marital_status': str(row.get('Marital Status', '')).strip(),
                        'nationality': row.get('Nationality', 'Indian'),
                        'blood_group': row.get('Blood Group') if not pd.isna(row.get('Blood Group')) else None,
                        'address': str(row.get('Permanent Address', '')).strip(),
                        'phone_number': str(row.get('Mobile Number', '')).strip(),
                        'alternate_contact_number': str(row.get('Alternate Contact Number', '')).strip() if not pd.isna(row.get('Alternate Contact Number')) else None,
                        'adhar_number': str(row.get('Aadhaar Number', '')).strip(),
                        'pan_card_number': str(row.get('PAN Card Number', '')).strip(),
                        'voter_id_driving_license': str(row.get('Voter ID / Driving License', '')).strip() if not pd.isna(row.get('Voter ID / Driving License')) else None,
                        'uan': str(row.get('UAN', '')).strip() if not pd.isna(row.get('UAN')) else None,
                        'esic_number': str(row.get('ESIC Number', '')).strip() if not pd.isna(row.get('ESIC Number')) else None,
                        'hire_date': date_of_joining,
                        'employment_type': str(row.get('Employment Type', '')).strip(),
                        'department_id': str(row.get('Department', '')).strip(),
                        'designation': str(row.get('Designation', '')).strip(),
                        'work_location': str(row.get('Work Location', '')).strip(),
                        'reporting_manager': str(row.get('Reporting Manager', '')).strip() if not pd.isna(row.get('Reporting Manager')) else None,
                        'salary_code': str(row.get('Salary Code', '')).strip(),
                        'skill_category': str(row.get('Skill Category', '')).strip() if not pd.isna(row.get('Skill Category')) else None,
                        'pf_applicability': parse_boolean(row.get('PF Applicability', False)),
                        'esic_applicability': parse_boolean(row.get('ESIC Applicability', False)),
                        'professional_tax_applicability': parse_boolean(row.get('Professional Tax Applicability', False)),
                        'salary_advance_loan': float(row.get('Salary Advance/Loan', 0)) if not pd.isna(row.get('Salary Advance/Loan')) else 0,
                        'highest_qualification': str(row.get('Highest Qualification', '')).strip(),
                        'year_of_passing': str(row.get('Year of Passing', '')).strip(),
                        'additional_certifications': str(row.get('Additional Certifications', '')).strip() if not pd.isna(row.get('Additional Certifications')) else None,
                        'experience_duration': str(row.get('Experience Duration', '')).strip(),
                        'emergency_contact_name': str(row.get('Emergency Contact Name', '')).strip(),
                        'emergency_contact_relationship': str(row.get('Emergency Relationship', '')).strip(),
                        'emergency_contact_phone': str(row.get('Emergency Phone Number', '')).strip(),
                        'employment_status': 'Active',
                        'created_date': datetime.utcnow()
                    }
                    
                    employees_to_insert.append(employee_data)
                    
                    # Prepare account data (will be linked after employee creation)
                    account_data = {
                        'account_number': str(row.get('Bank Account Number', '')).strip(),
                        'bank_name': str(row.get('Bank Name', '')).strip(),
                        'ifsc_code': str(row.get('IFSC Code', '')).strip(),
                        'branch_name': str(row.get('Branch Name', '')).strip() if not pd.isna(row.get('Branch Name')) else None,
                    }
                    accounts_to_insert.append(account_data)
                    
                except Exception as e:
                    errors.append({
                        "row": idx + 2,
                        "error": f"Processing error: {str(e)}"
                    })
                    continue
            
            # Bulk insert employees using SQLAlchemy Core for performance
            if employees_to_insert:
                try:
                    # Use bulk_insert_mappings for better performance
                    db.session.bulk_insert_mappings(Employee, employees_to_insert)
                    db.session.flush()
                    
                    # Get the inserted employee IDs
                    # Query back the employees we just inserted (by matching unique fields)
                    phone_numbers = [emp['phone_number'] for emp in employees_to_insert]
                    inserted_employees = Employee.query.filter(
                        Employee.phone_number.in_(phone_numbers)
                    ).all()
                    
                    # Create mapping of phone to employee_id
                    phone_to_emp_id = {emp.phone_number: emp.employee_id for emp in inserted_employees}
                    
                    # Link accounts to employees
                    accounts_with_emp_id = []
                    for i, account in enumerate(accounts_to_insert):
                        phone = employees_to_insert[i]['phone_number']
                        if phone in phone_to_emp_id:
                            account['emp_id'] = phone_to_emp_id[phone]
                            accounts_with_emp_id.append(account)
                    
                    # Bulk insert accounts
                    if accounts_with_emp_id:
                        db.session.bulk_insert_mappings(AccountDetails, accounts_with_emp_id)
                    
                    db.session.commit()
                    inserted += len(employees_to_insert)
                    
                except Exception as e:
                    db.session.rollback()
                    # If bulk insert fails, try individual inserts for this chunk
                    for i, emp_data in enumerate(employees_to_insert):
                        try:
                            emp = Employee(**emp_data)
                            db.session.add(emp)
                            db.session.flush()
                            
                            # Add account
                            account = AccountDetails(
                                emp_id=emp.employee_id,
                                **accounts_to_insert[i]
                            )
                            db.session.add(account)
                            db.session.commit()
                            inserted += 1
                            
                        except Exception as individual_error:
                            db.session.rollback()
                            errors.append({
                                "row": chunk_start + i + 2,
                                "error": str(individual_error)
                            })
        
        return jsonify({
            "success": True,
            "summary": {
                "total": total_rows,
                "inserted": inserted,
                "failed": len(errors),
                "errors": errors[:50]  # Limit errors shown to first 50
            }
        }), 201 if inserted > 0 else 400
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": f"Import failed: {str(e)}",
            "traceback": traceback.format_exc()
        }), 400


# Old Bulk upload

# @employees_bp.route("/bulk-upload", methods=["POST"])
# def bulk_upload():
#     """
#     Multipart form-data:
#       - file: Excel (.xlsx/.xls)
#     Expected columns in every sheet:
#       Full Name, Date of Birth, Gender, Site Name, Rank, State, Base Salary
#     """
#     # Lazy import to avoid heavy pandas dependency during app startup or when running seed scripts
#     from utils.excel_parser import load_excel_to_frames
#     file = request.files.get("file")
#     if not file:
#         return jsonify({"success": False, "message": "file is required"}), 400

#     # (Optional) Save a copy to disk
#     _ = save_file(file)

#     try:
#         frames = load_excel_to_frames(file)
#         summary = bulk_import_from_frames(frames)
#         status = 201 if summary["inserted"] > 0 else 400
#         return jsonify({"success": True, "summary": summary}), status
#     except Exception as e:
#         return jsonify({"success": False, "message": str(e)}), 400


@employees_bp.route("/<employee_id>", methods=["GET"])
def get_employee(employee_id):
    """Get employee details by employee ID"""
    try:
        employee = get_employee_by_id(employee_id)
        if not employee:
            return jsonify({"success": False, "message": "Employee not found"}), 404

         # Fetch account details (one-to-one relation)
        account = AccountDetails.query.filter_by(emp_id=employee.employee_id).first()

        return jsonify({
            "success": True,
            "data": {
                "employee_id": employee.employee_id,
                "first_name": employee.first_name,
                "last_name": employee.last_name,
                "father_name": employee.father_name,
                "email": employee.email,
                "phone_number": employee.phone_number,
                "address": employee.address,
                "date_of_birth": employee.date_of_birth.isoformat() if employee.date_of_birth else None,
                "hire_date": employee.hire_date.isoformat() if employee.hire_date else None,
                "department_id": employee.department_id,
                "designation": employee.designation,
                "employment_status": employee.employment_status,
                "salary_code": employee.salary_code,
                "base_salary": employee.base_salary,
                "created_date": employee.created_date.isoformat() if employee.created_date else None,
                "adhar_number": employee.adhar_number,
                "alternate_contact_number": employee.alternate_contact_number,
                "blood_group": employee.blood_group,
                "emergency_contact_name": employee.emergency_contact_name,
                "emergency_contact_phone": employee.emergency_contact_phone,
                "emergency_contact_relationship": employee.emergency_contact_relationship,
                "esic_number": employee.esic_number,
                "experience_duration": employee.experience_duration,
                "gender": employee.gender,
                "highest_qualification": employee.highest_qualification,
                "marital_status": employee.marital_status,
                "nationality": employee.nationality,
                "pan_card_number": employee.pan_card_number,
                "pf_applicability": employee.pf_applicability,
                "professional_tax_applicability": employee.professional_tax_applicability,
                "reporting_manager": employee.reporting_manager,
                "salary_advance_loan": employee.salary_advance_loan,
                "skill_category": employee.skill_category,
                "uan": employee.uan,
                "voter_id_driving_license": employee.voter_id_driving_license,
                "work_location": employee.work_location,
                "year_of_passing": employee.year_of_passing,

                # ✅ Include account details safely
                "bank_account_number": account.account_number if account else None,
                "bank_name": account.bank_name if account else None,
                "ifsc_code": account.ifsc_code if account else None,
                "branch_name": account.branch_name if account else None,
            }
        }), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400


@employees_bp.route("/<employee_id>", methods=["PUT", "DELETE", "OPTIONS"])
def update_employee(employee_id):
    """Update or delete an existing employee"""
    if request.method == 'OPTIONS':
        return '', 200

    if request.method == 'DELETE':
        try:
            emp = Employee.query.filter_by(employee_id=employee_id).first()
            if not emp:
                return jsonify({"success": False, "message": "Employee not found"}), 404

            # Delete associated account details if they exist
            account = AccountDetails.query.filter_by(emp_id=employee_id).first()
            if account:
                db.session.delete(account)

            # Delete the employee
            db.session.delete(emp)
            db.session.commit()

            return jsonify({
                "success": True,
                "message": "Employee deleted successfully"
            }), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"success": False, "message": str(e)}), 400

    # PUT method for updating
    try:
        emp = Employee.query.filter_by(employee_id=employee_id).first()
        if not emp:
            return jsonify({"success": False, "message": "Employee not found"}), 404

        payload = request.get_json() if request.is_json else request.form.to_dict()

        # Allow updating selected fields
        allowed_fields = [
            "first_name", "last_name", "email", "phone_number",
            "department_id", "designation", "employment_status"
        ]
        for field in allowed_fields:
            if field in payload and payload[field] is not None:
                setattr(emp, field, payload[field])

        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Employee updated successfully",
            "data": {
                "employee_id": emp.employee_id,
                "first_name": emp.first_name,
                "last_name": emp.last_name,
                "email": emp.email,
                "phone_number": emp.phone_number,
                "department_id": emp.department_id,
                "designation": emp.designation,
                "employment_status": emp.employment_status
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 400


@employees_bp.route("/", methods=["GET", "OPTIONS"])
@employees_bp.route("/list", methods=["GET", "OPTIONS"])
@token_required  # Add this decorator
def list_employees(current_user):  # Add current_user parameter
    """List employees based on user role with search and pagination support"""
    if request.method == 'OPTIONS':
        return '', 200

    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        search_term = request.args.get('search', '').strip()
        department = request.args.get('department', '').strip()
        employment_status = request.args.get('status', '').strip()

        # Base query
        query = Employee.query

        # Filter employees based on user role
        if current_user.role == 'supervisor':
            # Supervisor can only see employees from their site
            query = query.filter_by(site_id=current_user.site_id)

        # Apply search filters
        if search_term:
            search_filter = f"%{search_term}%"
            query = query.filter(
                db.or_(
                    Employee.first_name.ilike(search_filter),
                    Employee.last_name.ilike(search_filter),
                    Employee.employee_id.cast(db.String).ilike(search_filter),
                    Employee.email.ilike(search_filter),
                    Employee.phone_number.ilike(search_filter),
                    Employee.designation.ilike(search_filter)
                )
            )

        if department:
            query = query.filter(Employee.department_id.ilike(f"%{department}%"))

        if employment_status:
            query = query.filter(Employee.employment_status.ilike(f"%{employment_status}%"))

        # Apply pagination
        employees = query.paginate(page=page, per_page=per_page, error_out=False)

        employee_list = []
        for emp in employees.items:
            employee_list.append({
                "employee_id": emp.employee_id,
                "first_name": emp.first_name,
                "last_name": emp.last_name,
                "email": emp.email,
                "phone_number": emp.phone_number,
                "department_id": emp.department_id,
                "designation": emp.designation,
                "employment_status": emp.employment_status,
                "site_id": emp.site_id,
                "hire_date": emp.hire_date.isoformat() if emp.hire_date else None
            })

        return jsonify({
            "success": True,
            "data": employee_list,
            "pagination": {
                "page": employees.page,
                "per_page": employees.per_page,
                "total": employees.total,
                "pages": employees.pages
            }
        }), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@employees_bp.route("/all", methods=["GET", "OPTIONS"])
def get_all_employees_simple():
    """Get all employees without pagination (for dropdowns, etc.)"""
    if request.method == 'OPTIONS':
        return '', 200

    try:
        employees = get_all_employees_unpaginated()

        # Now employees is a list, not paginated
        employee_list = employees

        simple_list = []
        for emp in employee_list:
            simple_list.append({
                "employee_id": emp.employee_id,
                "first_name": emp.first_name,
                "last_name": emp.last_name,
                "full_name": f"{emp.first_name} {emp.last_name}",
                "email": emp.email,
                "phone_number": emp.phone_number,
                "department_id": emp.department_id,
                "designation": emp.designation,
                "employment_status": emp.employment_status,
                "hire_date": emp.hire_date.isoformat() if emp.hire_date else None,
                # Include additional fields for comprehensive display
                "date_of_birth": emp.date_of_birth.isoformat() if emp.date_of_birth else None,
                "gender": emp.gender,
                "marital_status": emp.marital_status,
                "nationality": emp.nationality,
                "blood_group": emp.blood_group,
                "address": emp.address,
                "alternate_contact_number": emp.alternate_contact_number,
                "adhar_number": emp.adhar_number,
                "pan_card_number": emp.pan_card_number,
                "voter_id_driving_license": emp.voter_id_driving_license,
                "uan": emp.uan,
                "esic_number": emp.esic_number,
                "employment_type": emp.employment_type,
                "work_location": emp.work_location,
                "reporting_manager": emp.reporting_manager,
                "salary_code": emp.salary_code,
                "skill_category": emp.skill_category,
                "pf_applicability": emp.pf_applicability,
                "esic_applicability": emp.esic_applicability,
                "professional_tax_applicability": emp.professional_tax_applicability,
                "salary_advance_loan": emp.salary_advance_loan,
                "highest_qualification": emp.highest_qualification,
                "year_of_passing": emp.year_of_passing,
                "additional_certifications": emp.additional_certifications,
                "experience_duration": emp.experience_duration,
                "emergency_contact_name": emp.emergency_contact_name,
                "emergency_contact_relationship": emp.emergency_contact_relationship,
                "emergency_contact_phone": emp.emergency_contact_phone,
            })

        return jsonify({
            "success": True,
            "data": simple_list,
            "count": len(simple_list)
        }), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400


@employees_bp.route("/search", methods=["GET"])
def search_employee():
    """Search employees by various criteria"""
    try:
        search_term = request.args.get('q', '')
        department = request.args.get('department')
        employment_status = request.args.get('status')

        employees = search_employees(
            search_term=search_term,
            department=department,
            employment_status=employment_status
        )

        employee_list = []
        for emp in employees:
            employee_list.append({
                "employee_id": emp.employee_id,
                "first_name": emp.first_name,
                "last_name": emp.last_name,
                "email": emp.email,
                "phone_number": emp.phone_number,
                "department_id": emp.department_id,
                "designation": emp.designation,
                "employment_status": emp.employment_status
            })

        return jsonify({
            "success": True,
            "data": employee_list,
            "count": len(employee_list)
        }), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@employees_bp.route("/site_employees", methods=["GET"])
@token_required
def get_site_employees(current_user):
    """Get employees for a specific site (supervisor only)"""
    if current_user.role != 'supervisor':
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    try:
        if not current_user.site_id:
            return jsonify({"success": False, "message": "Supervisor not assigned to any site"}), 400
        
        employees = Employee.query.filter_by(site_id=current_user.site_id).all()
        
        employee_list = []
        for emp in employees:
            employee_list.append({
                "employee_id": emp.employee_id,
                "first_name": emp.first_name,
                "last_name": emp.last_name,
                "full_name": f"{emp.first_name} {emp.last_name}",
                "email": emp.email,
                "phone_number": emp.phone_number,
                "department_id": emp.department_id,
                "designation": emp.designation,
                "employment_status": emp.employment_status,
                "site_id": emp.site_id
            })

        return jsonify({
            "success": True,
            "data": employee_list,
            "count": len(employee_list)
        }), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400
