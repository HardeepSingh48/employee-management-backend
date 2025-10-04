"""
Supervisor-specific attendance routes
"""
from flask import Blueprint, request, jsonify
from routes.auth import token_required
from models.employee import Employee
from models.attendance import Attendance


supervisor_attendance_bp = Blueprint("supervisor_attendance", __name__)


@supervisor_attendance_bp.route("/site-employees", methods=["GET"])
@token_required
def get_site_employees(current_user):
    """
    Get all employees for supervisor's site
    """
    if current_user.role not in ['supervisor', 'admin']:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    try:
        if current_user.role == 'supervisor':
            employees = Employee.query.filter_by(site_id=current_user.site_id).order_by(Employee.employee_id.asc()).all()
        else:
            employees = Employee.query.order_by(Employee.employee_id.asc()).all()
        
        employee_data = []
        for emp in employees:
            # Ensure full_name is never empty
            first_name = emp.first_name or ""
            last_name = emp.last_name or ""
            full_name = f"{first_name} {last_name}".strip()
            if not full_name:
                full_name = emp.employee_id  # Fallback to employee ID if no name

            employee_data.append({
                'employee_id': emp.employee_id,
                'first_name': emp.first_name,
                'last_name': emp.last_name,
                'full_name': full_name,
                'site_id': emp.site_id,
                'department_name': emp.department.department_name if emp.department else None,
                'designation': emp.designation
            })
        
        return jsonify({
            "success": True,
            "data": employee_data,
            "count": len(employee_data)
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error fetching site employees: {str(e)}"
        }), 500


@supervisor_attendance_bp.route("/site-attendance", methods=["GET"])
@token_required
def get_site_attendance(current_user):
    """
    Get attendance records for supervisor's site with filtering
    """
    if current_user.role not in ['supervisor', 'admin']:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    try:
        # Get query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        employee_id = request.args.get('employee_id')
        
        # Build query
        query = Attendance.query.join(Employee)
        
        if current_user.role