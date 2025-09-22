"""
Bulk attendance operations routes
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from routes.auth import token_required
from services.attendance_service import AttendanceService
from models.employee import Employee
from utils.attendance_helpers import round_to_half,validate_employee_access, validate_overtime_shifts



bulk_attendance_bp = Blueprint("bulk_attendance", __name__)


@bulk_attendance_bp.route("/bulk-mark", methods=["POST"])
@token_required
def bulk_mark_attendance(current_user):
    """
    Mark attendance for multiple employees (supervisor only)
    """
    if current_user.role not in ['supervisor', 'admin']:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    try:
        data = request.get_json()

        if not data or not data.get('attendance_records'):
            return jsonify({
                "success": False,
                "message": "No attendance records provided"
            }), 400

        attendance_records = data['attendance_records']
        marked_by = current_user.role

        # For supervisors, verify all employees belong to their site
        if current_user.role == 'supervisor':
            for record in attendance_records:
                is_valid, error_msg = validate_employee_access(current_user, record.get('employee_id'))
                if not is_valid:
                    return jsonify({
                        "success": False,
                        "message": error_msg
                    }), 403

        # Process datetime fields and overtime data for each record
        for record in attendance_records:
            if record.get('check_in_time'):
                record['check_in_time'] = datetime.fromisoformat(
                    record['check_in_time'].replace('Z', '+00:00')
                )

            if record.get('check_out_time'):
                record['check_out_time'] = datetime.fromisoformat(
                    record['check_out_time'].replace('Z', '+00:00')
                )
            
            # Handle overtime data with backward compatibility
            overtime_shifts = 0.0
            
            # Check for overtime_shifts first (new format)
            if 'overtime_shifts' in record:
                overtime_shifts = float(record['overtime_shifts'])
            # Backward compatibility: if overtime_hours is present, convert to shifts
            elif 'overtime_hours' in record:
                overtime_hours = float(record['overtime_hours'])
                overtime_shifts = round_to_half(overtime_hours / 8.0)
            
            # Validate overtime_shifts
            is_valid, error_msg = validate_overtime_shifts(overtime_shifts)
            if not is_valid:
                return jsonify({
                    "success": False, 
                    "message": f"{error_msg} for employee {record.get('employee_id')}"
                }), 400
            
            # Round to nearest 0.5 if not already
            overtime_shifts = round_to_half(overtime_shifts)
            record['overtime_shifts'] = overtime_shifts

        result = AttendanceService.bulk_mark_attendance(attendance_records, marked_by)

        return jsonify(result), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error in bulk attendance marking: {str(e)}"
        }), 500