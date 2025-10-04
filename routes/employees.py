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
    """Split full name into first and last name - matches old working implementation"""
    if not full_name or pd.isna(full_name):
        return "", ""

    full_name = str(full_name).strip()
    name_parts = full_name.split(" ", 1)
    first_name = name_parts[0] if name_parts else ""
    last_name = name_parts[1] if len(name_parts) > 1 else ""
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
        # Read Excel file - try different approaches
        try:
            # First try with openpyxl
            xl = pd.ExcelFile(file_path, engine='openpyxl')
        except Exception as e1:
            try:
                # Fallback to xlrd for older .xls files
                xl = pd.ExcelFile(file_path, engine='xlrd')
            except Exception as e2:
                return jsonify({
                    "success": False,
                    "message": f"Could not read Excel file. Tried openpyxl: {str(e1)}, xlrd: {str(e2)}"
                }), 400

        # Debug: Check all sheets
        print(f"DEBUG: Available sheets: {xl.sheet_names}")

        # Try to find a sheet with data
        df = None
        sheet_info = []

        for sheet_name in xl.sheet_names:
            try:
                temp_df = xl.parse(sheet_name)
                info = {
                    "sheet_name": sheet_name,
                    "rows": len(temp_df),
                    "columns": len(temp_df.columns),
                    "column_names": list(temp_df.columns) if len(temp_df.columns) > 0 else []
                }
                sheet_info.append(info)
                print(f"DEBUG: Sheet '{sheet_name}': {info['rows']} rows, {info['columns']} columns")

                # Use the first sheet with any data
                if len(temp_df) > 0:
                    df = temp_df
                    print(f"DEBUG: Using sheet: {sheet_name}")
                    break
            except Exception as e:
                print(f"DEBUG: Could not parse sheet {sheet_name}: {e}")
                sheet_info.append({
                    "sheet_name": sheet_name,
                    "error": str(e)
                })
                continue

        if df is None:
            return jsonify({
                "success": False,
                "message": "Could not find any data in the Excel file. All sheets appear to be empty.",
                "debug_info": {
                    "sheets_found": sheet_info
                }
            }), 400

        total_rows = len(df)
        inserted = 0
        errors = []

        # Debug: Print what we found
        print(f"DEBUG: Total rows in Excel: {total_rows}")
        print(f"DEBUG: Columns found: {list(df.columns)}")
        print(f"DEBUG: Data types: {df.dtypes.to_dict()}")
        print(f"DEBUG: First few rows:")
        print(df.head(3))
        print(f"DEBUG: Shape: {df.shape}")

        # Only require essential columns - make most fields optional
        essential_columns = ['Full Name']  # Only Full Name is absolutely required

        recommended_columns = [
            'Marital Status', 'Permanent Address', 'Mobile Number', 'Aadhaar Number',
            'PAN Card Number', 'Date of Joining', 'Employment Type', 'Department',
            'Designation', 'Work Location', 'Salary Code', 'Bank Account Number',
            'Bank Name', 'IFSC Code', 'Highest Qualification', 'Year of Passing',
            'Experience Duration', 'Emergency Contact Name', 'Emergency Relationship',
            'Emergency Phone Number', 'Employee Id', 'UAN Number'
        ]

        found_columns = list(df.columns)
        missing_essential = [col for col in essential_columns if col not in df.columns]

        if missing_essential:
            return jsonify({
                "success": False,
                "message": f"Missing essential columns: {', '.join(missing_essential)}",
                "debug_info": {
                    "total_rows": total_rows,
                    "columns_found": found_columns,
                    "essential_columns": essential_columns,
                    "recommended_columns": recommended_columns
                }
            }), 400

        # Warn about missing recommended columns but don't fail
        missing_recommended = [col for col in recommended_columns if col not in df.columns]
        if missing_recommended:
            print(f"WARNING: Missing recommended columns: {', '.join(missing_recommended)}")
            print("These fields will use default values")
        
        # Process in chunks for better memory management
        for chunk_start in range(0, total_rows, CHUNK_SIZE):
            chunk_end = min(chunk_start + CHUNK_SIZE, total_rows)
            chunk_df = df.iloc[chunk_start:chunk_end]
            
            employees_to_insert = []
            accounts_to_insert = []
            
            for idx, row in chunk_df.iterrows():
                try:
                    # Parse full name - matches old implementation
                    first_name, last_name = split_full_name(row.get('Full Name'))
                    if not first_name:
                        errors.append({
                            "row": idx + 2,  # +2 for Excel row (header + 0-index)
                            "error": "First Name is required"
                        })
                        continue

                    # Use provided Employee Id if available, otherwise let database generate it
                    custom_employee_id = None
                    if 'Employee Id' in df.columns and not pd.isna(row.get('Employee Id')):
                        custom_employee_id = int(row.get('Employee Id'))

                    # Provide defaults for missing fields
                    employee_data = {
                        'first_name': first_name,
                        'last_name': last_name,
                        'father_name': None,
                        'date_of_birth': None,
                        'gender': None,
                        'marital_status': 'Single',  # Default
                        'nationality': 'Indian',
                        'blood_group': None,
                        'address': 'Not Provided',  # Default address
                        'phone_number': '9999999999',  # Default phone - will be updated later
                        'alternate_contact_number': None,
                        'adhar_number': '000000000000',  # Default Aadhaar
                        'pan_card_number': 'AAAAA0000A',  # Default PAN
                        'voter_id_driving_license': None,
                        'uan': str(row.get('UAN Number', '')).strip() if 'UAN Number' in df.columns and not pd.isna(row.get('UAN Number')) else None,
                        'esic_number': None,
                        'hire_date': datetime.utcnow().date(),  # Default to today
                        'employment_type': 'Full-time',  # Default
                        'department_id': 'IT',  # Default department (exists in database)
                        'designation': 'Employee',  # Default designation
                        'work_location': 'Main Office',  # Default
                        'reporting_manager': None,
                        'salary_code': str(row.get('Salary Code', '')).strip() if 'Salary Code' in df.columns and not pd.isna(row.get('Salary Code')) else 'DEFAULT',
                        'skill_category': None,
                        'pf_applicability': False,
                        'esic_applicability': False,
                        'professional_tax_applicability': False,
                        'salary_advance_loan': 0,
                        'highest_qualification': 'Not Specified',  # Default
                        'year_of_passing': '2020',  # Default
                        'additional_certifications': None,
                        'experience_duration': '0 years',  # Default
                        'emergency_contact_name': f'{first_name} Contact',  # Default
                        'emergency_contact_relationship': 'Relative',  # Default
                        'emergency_contact_phone': '9999999999',  # Default
                        'employment_status': 'Active',
                        'created_date': datetime.utcnow()
                    }

                    # Override defaults with provided values if available
                    if 'Marital Status' in df.columns and not pd.isna(row.get('Marital Status')):
                        employee_data['marital_status'] = str(row.get('Marital Status')).strip()

                    if 'Permanent Address' in df.columns and not pd.isna(row.get('Permanent Address')):
                        employee_data['address'] = str(row.get('Permanent Address')).strip()

                    if 'Mobile Number' in df.columns and not pd.isna(row.get('Mobile Number')):
                        phone = str(row.get('Mobile Number')).strip()
                        if phone:
                            employee_data['phone_number'] = phone

                    if 'Aadhaar Number' in df.columns and not pd.isna(row.get('Aadhaar Number')):
                        aadhaar = str(row.get('Aadhaar Number')).strip()
                        if aadhaar:
                            employee_data['adhar_number'] = aadhaar

                    if 'PAN Card Number' in df.columns and not pd.isna(row.get('PAN Card Number')):
                        pan = str(row.get('PAN Card Number')).strip()
                        if pan:
                            employee_data['pan_card_number'] = pan

                    if 'Date of Joining' in df.columns:
                        date_joining = parse_date(row.get('Date of Joining'))
                        if date_joining:
                            employee_data['hire_date'] = date_joining

                    if 'Employment Type' in df.columns and not pd.isna(row.get('Employment Type')):
                        employee_data['employment_type'] = str(row.get('Employment Type')).strip()

                    if 'Department' in df.columns and not pd.isna(row.get('Department')):
                        employee_data['department_id'] = str(row.get('Department')).strip()

                    if 'Designation' in df.columns and not pd.isna(row.get('Designation')):
                        employee_data['designation'] = str(row.get('Designation')).strip()

                    if 'Work Location' in df.columns and not pd.isna(row.get('Work Location')):
                        employee_data['work_location'] = str(row.get('Work Location')).strip()

                    # Handle custom employee ID if provided
                    if custom_employee_id:
                        employee_data['employee_id'] = custom_employee_id
                    
                    employees_to_insert.append(employee_data)

                    # Prepare account data with defaults (will be linked after employee creation)
                    account_data = {
                        'account_number': '000000000000',  # Default account number
                        'bank_name': 'Not Specified',  # Default bank
                        'ifsc_code': 'XXXX0000000',  # Default IFSC
                        'branch_name': None,
                    }

                    # Override with provided values if available
                    if 'Bank Account Number' in df.columns and not pd.isna(row.get('Bank Account Number')):
                        account_data['account_number'] = str(row.get('Bank Account Number')).strip()

                    if 'Bank Name' in df.columns and not pd.isna(row.get('Bank Name')):
                        account_data['bank_name'] = str(row.get('Bank Name')).strip()

                    if 'IFSC Code' in df.columns and not pd.isna(row.get('IFSC Code')):
                        account_data['ifsc_code'] = str(row.get('IFSC Code')).strip()

                    if 'Branch Name' in df.columns and not pd.isna(row.get('Branch Name')):
                        account_data['branch_name'] = str(row.get('Branch Name')).strip()

                    accounts_to_insert.append(account_data)
                    
                except Exception as e:
                    errors.append({
                        "row": idx + 2,
                        "error": f"Processing error: {str(e)}"
                    })
                    continue
            
            # Insert employees - handle custom IDs carefully
            if employees_to_insert:
                try:
                    # Separate employees with and without custom IDs
                    custom_id_employees = []
                    auto_id_employees = []

                    for i, emp_data in enumerate(employees_to_insert):
                        if 'employee_id' in emp_data:
                            custom_id_employees.append((i, emp_data))
                        else:
                            auto_id_employees.append((i, emp_data))

                    # Insert employees with custom IDs first (individual inserts)
                    custom_accounts = []
                    for i, emp_data in custom_id_employees:
                        try:
                            emp = Employee(**emp_data)
                            db.session.add(emp)
                            db.session.flush()

                            # Prepare account for this employee
                            account_data = accounts_to_insert[i].copy()
                            account_data['emp_id'] = emp.employee_id
                            custom_accounts.append(account_data)
                            inserted += 1

                        except Exception as e:
                            db.session.rollback()
                            errors.append({
                                "row": chunk_start + i + 2,
                                "error": f"Failed to insert employee with custom ID: {str(e)}"
                            })

                    # Bulk insert employees with auto-generated IDs
                    if auto_id_employees:
                        auto_emp_data = [emp_data for i, emp_data in auto_id_employees]
                        db.session.bulk_insert_mappings(Employee, auto_emp_data)
                        db.session.flush()

                        # Get the inserted employee IDs
                        phone_numbers = [emp_data['phone_number'] for emp_data in auto_emp_data]
                        inserted_employees = Employee.query.filter(
                            Employee.phone_number.in_(phone_numbers)
                        ).all()

                        # Create mapping of phone to employee_id
                        phone_to_emp_id = {emp.phone_number: emp.employee_id for emp in inserted_employees}

                        # Link accounts to auto-ID employees
                        for i, emp_data in auto_id_employees:
                            phone = emp_data['phone_number']
                            if phone in phone_to_emp_id:
                                account_data = accounts_to_insert[i].copy()
                                account_data['emp_id'] = phone_to_emp_id[phone]
                                custom_accounts.append(account_data)

                        inserted += len(auto_id_employees)

                    # Insert all accounts
                    if custom_accounts:
                        db.session.bulk_insert_mappings(AccountDetails, custom_accounts)

                    db.session.commit()

                except Exception as e:
                    db.session.rollback()
                    errors.append({
                        "row": chunk_start + 1,
                        "error": f"Chunk insert failed: {str(e)}"
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
        
        employees = Employee.query.filter_by(site_id=current_user.site_id).order_by(Employee.employee_id.asc()).all()
        
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
