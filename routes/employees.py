from flask import Blueprint, request, jsonify
from services.employee_service import create_employee, bulk_import_from_frames, get_employee_by_id, get_all_employees, search_employees
from utils.upload import save_file

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
                "salary_code": emp.salary_code
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
                "created_date": employee.created_date.isoformat() if employee.created_date else None
            }
        }), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400


@employees_bp.route("/", methods=["GET", "OPTIONS"])
@employees_bp.route("/list", methods=["GET", "OPTIONS"])
def list_employees():
    """List all employees with pagination"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))

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
