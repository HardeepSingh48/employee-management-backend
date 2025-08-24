from flask import Blueprint, request, jsonify
from services.employee_service import create_employee, bulk_import_from_frames, get_employee_by_id, get_all_employees, search_employees
from models import db
from models.employee import Employee
from utils.upload import save_file
from models.account_details import AccountDetails
from routes.auth import token_required

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


@employees_bp.route("/bulk-upload", methods=["POST"])
def bulk_upload():
    """
    Multipart form-data:
      - file: Excel (.xlsx/.xls)
    Expected columns in every sheet:
      Full Name, Date of Birth, Gender, Site Name, Rank, State, Base Salary
    """
    # Lazy import to avoid heavy pandas dependency during app startup or when running seed scripts
    from utils.excel_parser import load_excel_to_frames
    file = request.files.get("file")
    if not file:
        return jsonify({"success": False, "message": "file is required"}), 400

    # (Optional) Save a copy to disk
    _ = save_file(file)

    try:
        frames = load_excel_to_frames(file)
        summary = bulk_import_from_frames(frames)
        status = 201 if summary["inserted"] > 0 else 400
        return jsonify({"success": True, "summary": summary}), status
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400


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


@employees_bp.route("/<employee_id>", methods=["PUT", "OPTIONS"])
def update_employee(employee_id):
    """Update an existing employee's basic details"""
    if request.method == 'OPTIONS':
        return '', 200

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
    """List employees based on user role"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        
        # Filter employees based on user role
        if current_user.role == 'supervisor':
            # Supervisor can only see employees from their site
            employees = Employee.query.filter_by(site_id=current_user.site_id)\
                                    .paginate(page=page, per_page=per_page, error_out=False)
        else:
            # Admin/HR can see all employees
            employees = get_all_employees(page=page, per_page=per_page)
        
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
    try:
        employees = get_all_employees()

        # Handle both paginated and non-paginated results
        if hasattr(employees, 'items'):
            employee_list = employees.items
        else:
            employee_list = employees

        simple_list = []
        for emp in employee_list:
            simple_list.append({
                "employee_id": emp.employee_id,
                "first_name": emp.first_name,
                "last_name": emp.last_name,
                "full_name": f"{emp.first_name} {emp.last_name}",
                "email": emp.email,
                "department_id": emp.department_id,
                "employment_status": emp.employment_status
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
